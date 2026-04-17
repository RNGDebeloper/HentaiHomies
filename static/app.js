document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("searchToggle");
  const input = document.getElementById("searchInput");
  const submit = document.getElementById("searchSubmit");

  if (toggle && input && submit) {
    toggle.addEventListener("click", () => {
      const expanded = input.style.width && input.style.width !== "0px" && input.style.width !== "0";
      if (!expanded) {
        input.style.width = "250px";
        input.style.opacity = "1";
        submit.style.display = "inline-block";
        input.focus();
      } else {
        input.style.width = "0";
        input.style.opacity = "0";
        submit.style.display = "none";
      }
    });
  }

  const overlay = document.getElementById("loadingOverlay");
  const activatingElements = document.querySelectorAll("a[data-loading], button[data-loading]");
  activatingElements.forEach((element) => {
    element.addEventListener("click", () => {
      if (overlay) overlay.classList.add("active");
    });
  });
});
