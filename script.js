// Small progressive enhancements for the existing Flask templates.
document.addEventListener("DOMContentLoaded", () => {
  const navToggle = document.querySelector("[data-nav-toggle]");
  const navLinks = document.querySelector("[data-nav-links]");
  if (navToggle && navLinks) navToggle.addEventListener("click", () => {
    const isOpen = navLinks.classList.toggle("is-open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });
  const passwordToggle = document.querySelector("[data-password-toggle]");
  const passwordInput = document.querySelector("#password");
  if (passwordToggle && passwordInput) passwordToggle.addEventListener("click", () => {
    const show = passwordInput.type === "password";
    passwordInput.type = show ? "text" : "password";
    passwordToggle.textContent = show ? "Hide" : "Show";
    passwordToggle.setAttribute("aria-label", show ? "Hide password" : "Show password");
  });
});

  // Persist the selected appearance across pages and browser sessions.
  const themeToggle = document.querySelector("[data-theme-toggle]");
  const themeIcon = document.querySelector("[data-theme-icon]");
  const applyTheme = (theme) => {
    document.body.dataset.theme = theme;
    if (themeIcon) themeIcon.textContent = theme === "dark" ? "☀" : "☾";
    if (themeToggle) {
      const label = theme === "dark" ? "Switch to light appearance" : "Switch to dark appearance";
      themeToggle.setAttribute("aria-label", label);
      themeToggle.setAttribute("title", label);
    }
  };
  let savedTheme = "light";
  try { savedTheme = localStorage.getItem("athlete-theme") || "light"; } catch (_) {}
  applyTheme(savedTheme === "dark" ? "dark" : "light");
  if (themeToggle) themeToggle.addEventListener("click", () => {
    const nextTheme = document.body.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(nextTheme);
    try { localStorage.setItem("athlete-theme", nextTheme); } catch (_) {}
  });
