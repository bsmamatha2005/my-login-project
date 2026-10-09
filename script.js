(() => {
  const API_BASE_URL = (window.API_BASE_URL || "").replace(/\/+$/, "");
  const $ = (id) => document.getElementById(id);
  const tokenKey = "login_demo_token";

  function message(text, good = false) {
    $("message").textContent = text;
    $("message").style.color = good ? "#067647" : "#b42318";
  }

  async function api(path, { method = "GET", body, auth = false } = {}) {
    const headers = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (auth) {
      const token = sessionStorage.getItem(tokenKey);
      if (token) headers.Authorization = `Bearer ${token}`;
    }
    let response;
    try {
      response = await fetch(`${API_BASE_URL}${path}`, {
        method, headers,
        body: body === undefined ? undefined : JSON.stringify(body)
      });
    } catch {
      throw new Error("Cannot reach the backend. Check the Render URL and CORS settings.");
    }
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || "Request failed.");
    return result;
  }

  function showTab(which) {
    const login = which === "login";
    $("login-form").classList.toggle("hidden", !login);
    $("register-form").classList.toggle("hidden", login);
    $("login-tab").classList.toggle("active", login);
    $("register-tab").classList.toggle("active", !login);
    message("");
  }

  function showDashboard(user) {
    $("auth-panel").classList.add("hidden");
    $("dashboard").classList.remove("hidden");
    $("profile-text").textContent = `${user.name} · ${user.email}`;
    message("You are signed in.", true);
  }

  function showAuth() {
    $("dashboard").classList.add("hidden");
    $("auth-panel").classList.remove("hidden");
  }

  $("login-tab").addEventListener("click", () => showTab("login"));
  $("register-tab").addEventListener("click", () => showTab("register"));

  $("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const result = await api("/api/login", {
        method: "POST",
        body: { email: form.get("email"), password: form.get("password") }
      });
      sessionStorage.setItem(tokenKey, result.access_token);
      showDashboard(result.user);
      event.currentTarget.reset();
    } catch (error) { message(error.message); }
  });

  $("register-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const result = await api("/api/register", {
        method: "POST",
        body: {
          name: form.get("name"),
          email: form.get("email"),
          password: form.get("password")
        }
      });
      sessionStorage.setItem(tokenKey, result.access_token);
      showDashboard(result.user);
      event.currentTarget.reset();
    } catch (error) { message(error.message); }
  });

  $("logout-button").addEventListener("click", () => {
    sessionStorage.removeItem(tokenKey);
    showAuth();
    showTab("login");
    message("You have logged out.", true);
  });

  // Restore session while the tab remains open.
  if (sessionStorage.getItem(tokenKey)) {
    api("/api/me", { auth: true })
      .then(result => showDashboard(result.user))
      .catch(() => {
        sessionStorage.removeItem(tokenKey);
        showAuth();
      });
  }

  if (!API_BASE_URL) message("Set API_BASE_URL in config.js before using the app.");
})();
