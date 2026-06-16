const navToggle = document.querySelector(".nav-toggle");
const navLinks = document.querySelector(".site-nav__links");

if (navToggle && navLinks) {
  navToggle.addEventListener("click", () => {
    const isOpen = navLinks.classList.toggle("is-open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });

  navLinks.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      navLinks.classList.remove("is-open");
      navToggle.setAttribute("aria-expanded", "false");
    });
  });
}

document.querySelectorAll("[data-close-toast]").forEach((button) => {
  button.addEventListener("click", () => {
    const toast = document.getElementById("profile-toast");
    if (toast) {
      toast.classList.add("is-hidden");
    }
  });
});
