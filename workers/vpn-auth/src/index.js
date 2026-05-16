// Cloudflare Worker Authentication API for Mirage VPN
// Handles registration, login, token verification, and email OTP verification via Resend

const pbkdf2Config = {
  name: "PBKDF2",
  hash: "SHA-256",
  iterations: 100000
};

// --- Crypto Utilities ---
async function hashPassword(password, saltString = null) {
  const encoder = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    encoder.encode(password),
    { name: "PBKDF2" },
    false,
    ["deriveBits", "deriveKey"]
  );

  let saltBuffer;
  if (saltString) {
    const binary = atob(saltString);
    saltBuffer = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) saltBuffer[i] = binary.charCodeAt(i);
  } else {
    saltBuffer = crypto.getRandomValues(new Uint8Array(16));
  }

  const key = await crypto.subtle.deriveKey(
    { name: "PBKDF2", salt: saltBuffer, iterations: pbkdf2Config.iterations, hash: pbkdf2Config.hash },
    keyMaterial,
    { name: "AES-GCM", length: 256 },
    true,
    ["encrypt", "decrypt"]
  );

  const rawHash = await crypto.subtle.exportKey("raw", key);
  const hashHex = Array.from(new Uint8Array(rawHash)).map(b => b.toString(16).padStart(2, '0')).join('');
  const saltB64 = btoa(String.fromCharCode(...saltBuffer));

  return `${saltB64}:${hashHex}`;
}

async function verifyPassword(password, storedHash) {
  const [saltB64, hashHex] = storedHash.split(':');
  if (!saltB64 || !hashHex) return false;
  const newHash = await hashPassword(password, saltB64);
  return newHash === storedHash;
}

function generateOTP() {
  return Math.floor(100000 + Math.random() * 900000).toString();
}

function generateToken() {
  const buf = crypto.getRandomValues(new Uint8Array(32));
  return Array.from(buf).map(b => b.toString(16).padStart(2, '0')).join('');
}

// --- Supabase Utilities ---
async function supabaseRequest(env, path, method = "GET", body = null) {
  const headers = {
    "apikey": env.SUPABASE_KEY,
    "Authorization": `Bearer ${env.SUPABASE_KEY}`,
    "Content-Type": "application/json",
    "Prefer": "return=representation"
  };
  
  const options = { method, headers };
  if (body) options.body = JSON.stringify(body);

  const res = await fetch(`${env.SUPABASE_URL}/rest/v1${path}`, options);
  const data = await res.json();
  return { status: res.status, data };
}

// --- Resend Utility ---
async function sendEmailOTP(env, to, code) {
  // We use ctx.waitUntil in the main handler or just await it depending on needs.
  // Using direct fetch to resend API
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.RESEND_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      from: `Mirage VPN <${env.FROM_EMAIL}>`,
      to,
      subject: 'Your Mirage VPN Verification Code',
      html: `
        <div style="font-family: sans-serif; max-width: 500px; margin: 0 auto; color: #1a1a2e; padding: 20px;">
          <h2 style="color: #2A5AFF;">Mirage VPN Registration</h2>
          <p>Thank you for signing up for Mirage VPN. To activate your account, please use the following 6-digit verification code:</p>
          <div style="background: #f4f6fc; border: 1px solid #dce2f2; padding: 16px; border-radius: 8px; text-align: center; margin: 24px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #1a1a2e;">${code}</span>
          </div>
          <p>This code will expire in 10 minutes.</p>
          <p style="font-size: 12px; color: #8A857E; margin-top: 32px;">If you didn't request this, you can safely ignore this email.</p>
        </div>
      `
    })
  });
  
  if (!res.ok) {
    const errorBody = await res.text();
    console.error("Resend API error:", errorBody);
    throw new Error(`Failed to send email: ${res.status} ${res.statusText}`);
  }
  return await res.json();
}

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

// --- Handlers ---
async function handleRegister(request, env) {
  const { username, email, password } = await request.json();
  if (!username || !email || !password) return Response.json({ error: "Missing fields" }, { status: 400, headers: CORS_HEADERS });

  // Check if username or email exists
  const checkRes = await supabaseRequest(env, `/users?or=(username.eq.${encodeURIComponent(username)},email.eq.${encodeURIComponent(email)})`);
  if (checkRes.data && checkRes.data.length > 0) {
    return Response.json({ error: "Username or email already exists" }, { status: 400, headers: CORS_HEADERS });
  }

  const hashedPassword = await hashPassword(password);
  
  // Insert user (is_verified = false by default in DB)
  const insertUserRes = await supabaseRequest(env, `/users`, "POST", {
    username,
    email,
    password_hash: hashedPassword,
    is_verified: false
  });
  
  if (insertUserRes.status > 299) {
    return Response.json({ error: "Failed to create user", details: insertUserRes.data }, { status: 500, headers: CORS_HEADERS });
  }
  
  const user = insertUserRes.data[0];
  const otp = generateOTP();
  
  // Insert Verification Code (expires in 10 minutes using Postgres NOW() + INTERVAL logic in schema)
  await supabaseRequest(env, `/verification_codes`, "POST", {
    user_id: user.id,
    code: otp
  });

  // Send Email
  try {
    await sendEmailOTP(env, user.email, otp);
  } catch (err) {
    console.error("Mail send error:", err);
    // Continue even if email fails, user can request a resend
  }

  return Response.json({ success: true, message: "Account created. Please check your email for the OTP.", user_id: user.id }, { headers: CORS_HEADERS });
}

async function handleResendCode(request, env) {
  const { email } = await request.json();
  if (!email) return Response.json({ error: "Email is required" }, { status: 400, headers: CORS_HEADERS });

  const userRes = await supabaseRequest(env, `/users?email=eq.${encodeURIComponent(email)}`);
  if (!userRes.data || userRes.data.length === 0) {
    return Response.json({ error: "User not found" }, { status: 404, headers: CORS_HEADERS });
  }
  
  const user = userRes.data[0];
  if (user.is_verified) {
    return Response.json({ error: "Account is already verified" }, { status: 400, headers: CORS_HEADERS });
  }

  // Delete previous codes
  await supabaseRequest(env, `/verification_codes?user_id=eq.${user.id}`, "DELETE");

  const otp = generateOTP();
  await supabaseRequest(env, `/verification_codes`, "POST", {
    user_id: user.id,
    code: otp
  });

  try {
    await sendEmailOTP(env, user.email, otp);
  } catch (err) {
    return Response.json({ error: "Failed to send email" }, { status: 500, headers: CORS_HEADERS });
  }

  return Response.json({ success: true, message: "A new code has been sent." }, { headers: CORS_HEADERS });
}

async function handleVerifyEmail(request, env) {
  const { email, code } = await request.json();
  if (!email || !code) return Response.json({ error: "Email and code are required" }, { status: 400, headers: CORS_HEADERS });

  const userRes = await supabaseRequest(env, `/users?email=eq.${encodeURIComponent(email)}`);
  if (!userRes.data || userRes.data.length === 0) return Response.json({ error: "User not found" }, { status: 404, headers: CORS_HEADERS });
  
  const user = userRes.data[0];

  // Fetch codes for this user that haven't expired
  const codeRes = await supabaseRequest(env, `/verification_codes?user_id=eq.${user.id}&code=eq.${encodeURIComponent(code)}&order=created_at.desc&limit=1`);
  
  if (!codeRes.data || codeRes.data.length === 0) {
    return Response.json({ error: "Invalid or expired code" }, { status: 400, headers: CORS_HEADERS });
  }

  const codeRecord = codeRes.data[0];
  const expiresAt = new Date(codeRecord.expires_at).getTime();
  if (Date.now() > expiresAt) {
    return Response.json({ error: "Code has expired. Please request a new one." }, { status: 400, headers: CORS_HEADERS });
  }

  // Code is valid - update user to verified
  await supabaseRequest(env, `/users?id=eq.${user.id}`, "PATCH", { is_verified: true });
  
  // Clean up codes
  await supabaseRequest(env, `/verification_codes?user_id=eq.${user.id}`, "DELETE");

  return Response.json({ success: true, message: "Account verified successfully. You can now sign in." }, { headers: CORS_HEADERS });
}

async function handleLogin(request, env) {
  const { username, password } = await request.json();
  if (!username || !password) return Response.json({ error: "Missing fields" }, { status: 400, headers: CORS_HEADERS });

  const isEmail = username.includes('@');
  const queryField = isEmail ? 'email' : 'username';
  const userRes = await supabaseRequest(env, `/users?${queryField}=eq.${encodeURIComponent(username)}`);
  
  if (!userRes.data || userRes.data.length === 0) {
    return Response.json({ error: "Invalid credentials" }, { status: 401, headers: CORS_HEADERS });
  }

  const user = userRes.data[0];

  // Brute force protection check
  if (user.locked_until && new Date(user.locked_until).getTime() > Date.now()) {
    return Response.json({ error: "Account locked due to too many failed attempts. Try again later." }, { status: 403, headers: CORS_HEADERS });
  }

  // Verify password
  let isValid = false;
  if (user.password_hash.includes(':')) {
    // New format (salt:hash)
    isValid = await verifyPassword(password, user.password_hash);
  } else {
    // Legacy format handling or fail
    isValid = false;
  }

  if (!isValid) {
    // Increment failed attempts
    const newAttempts = (user.failed_attempts || 0) + 1;
    let updates = { failed_attempts: newAttempts };
    if (newAttempts >= 5) {
      updates.locked_until = new Date(Date.now() + 15 * 60000).toISOString(); // 15 mins
    }
    await supabaseRequest(env, `/users?id=eq.${user.id}`, "PATCH", updates);
    return Response.json({ error: "Invalid credentials" }, { status: 401, headers: CORS_HEADERS });
  }

  // Check if verified
  if (user.is_verified === false) {
    // Reset failed attempts since password was valid
    await supabaseRequest(env, `/users?id=eq.${user.id}`, "PATCH", { failed_attempts: 0 });
    return Response.json({ error: "Please verify your email first", email: user.email, requires_verification: true }, { status: 403, headers: CORS_HEADERS });
  }

  // Success login
  const token = generateToken();
  const resetRes = await supabaseRequest(env, `/users?id=eq.${user.id}`, "PATCH", { 
    failed_attempts: 0, 
    locked_until: null 
  });

  // Get client IP
  const ip = request.headers.get("CF-Connecting-IP") || "";

  // Insert session
  await supabaseRequest(env, `/sessions`, "POST", {
    user_id: user.id,
    token: token,
    ip_address: ip
  });

  return Response.json({ success: true, token, username: user.username }, { headers: CORS_HEADERS });
}

async function handleVerify(request, env) {
  // This endpoint is used internally by the Python VPN server to validate tokens
  const { token } = await request.json();
  if (!token) return Response.json({ valid: false }, { status: 400, headers: CORS_HEADERS });

  const sessionRes = await supabaseRequest(env, `/sessions?token=eq.${token}&is_active=eq.true`);
  if (!sessionRes.data || sessionRes.data.length === 0) {
    return Response.json({ valid: false }, { headers: CORS_HEADERS });
  }

  const session = sessionRes.data[0];
  const expiresAt = new Date(session.expires_at).getTime();
  if (Date.now() > expiresAt) {
    await supabaseRequest(env, `/sessions?id=eq.${session.id}`, "PATCH", { is_active: false });
    return Response.json({ valid: false }, { headers: CORS_HEADERS });
  }

  return Response.json({ valid: true, user_id: session.user_id }, { headers: CORS_HEADERS });
}

export default {
  async fetch(request, env, ctx) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS_HEADERS });
    }

    try {
      const url = new URL(request.url);
      const path = url.pathname;

      if (request.method === "POST") {
        if (path === "/register") return await handleRegister(request, env);
        if (path === "/login") return await handleLogin(request, env);
        if (path === "/verify") return await handleVerify(request, env);
        if (path === "/verify-email") return await handleVerifyEmail(request, env);
        if (path === "/resend-code") return await handleResendCode(request, env);
      }

      return Response.json({ error: "Not found" }, { status: 404, headers: CORS_HEADERS });
    } catch (e) {
      console.error("Worker error:", e);
      return Response.json({ error: e.message || "Internal server error" }, { status: 500, headers: CORS_HEADERS });
    }
  }
};