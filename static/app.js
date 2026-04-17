function setupRetryButtons() {
  document.querySelectorAll('[data-retry-url]').forEach((button) => {
    button.addEventListener('click', () => {
      const url = button.getAttribute('data-retry-url');
      if (url) window.location.href = url;
    });
  });
}

document.addEventListener('DOMContentLoaded', setupRetryButtons);
