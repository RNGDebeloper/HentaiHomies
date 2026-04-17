function setupRetryButtons() {
  document.querySelectorAll('[data-retry-url]').forEach((button) => {
    button.addEventListener('click', () => {
      const url = button.getAttribute('data-retry-url');
      if (url) window.location.href = url;
    });
  });
}

function escapeHtml(input) {
  return String(input ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function brandCard(brand) {
  const logo = brand.logo_url
    ? `<img src="/proxy?url=${encodeURIComponent(brand.logo_url)}" alt="${escapeHtml(brand.title)}" class="brand-logo" loading="lazy">`
    : '<div class="brand-logo fallback"><i class="fa-solid fa-building"></i></div>';

  const website = brand.website_url
    ? `<a href="${escapeHtml(brand.website_url)}" target="_blank" rel="noopener" class="small">Website</a>`
    : '<span class="small text-secondary">No website</span>';

  return `
    <article class="browse-card">
      ${logo}
      <h3 class="h6 mb-1 mt-2">${escapeHtml(brand.title)}</h3>
      <div class="meta mb-2">slug: ${escapeHtml(brand.slug || 'n/a')} · count: ${escapeHtml(brand.count ?? 0)}</div>
      <div class="d-flex justify-content-between align-items-center">
        <a class="btn btn-sm btn-outline-info" href="/browse/brands/${encodeURIComponent(brand.slug || '')}/0">Open</a>
        ${website}
      </div>
    </article>
  `;
}

function categoryCard(item, key) {
  const image = item.image_url
    ? `<img src="/proxy?url=${encodeURIComponent(item.image_url)}" alt="${escapeHtml(item.title)}" loading="lazy">`
    : '<div class="cat-image fallback"><i class="fa-solid fa-folder-open"></i></div>';

  return `
    <article class="browse-card compact">
      ${image}
      <h4 class="h6 mb-1 mt-2">${escapeHtml(item.title)}</h4>
      <div class="meta mb-2">${escapeHtml(item.slug || 'n/a')} · ${escapeHtml(item.count ?? 0)}</div>
      <a class="btn btn-sm btn-outline-light" href="/browse/${encodeURIComponent(key)}/${encodeURIComponent(item.slug || item.title)}/0">Browse</a>
    </article>
  `;
}

async function loadBrowseData(forceRefresh = false) {
  const loading = document.getElementById('browseLoading');
  const errorEl = document.getElementById('browseError');
  if (!loading) return;

  loading.classList.remove('d-none');
  errorEl.classList.add('d-none');

  try {
    const endpoint = forceRefresh ? '/api/browse?refresh=1' : '/api/browse';
    const res = await fetch(endpoint, { method: 'GET' });
    if (!res.ok) {
      const payload = await res.json().catch(() => ({}));
      throw new Error(payload.error || `Browse request failed (${res.status})`);
    }

    const data = await res.json();

    const metadata = data.metadata || {};
    const metaBox = document.getElementById('browseMeta');
    metaBox.classList.remove('d-none');
    metaBox.innerHTML = `
      <h2 class="h6 mb-3">Metadata</h2>
      <div class="stat-grid">
        ${Object.entries(metadata)
          .map(([key, value]) => `<div class="stat-chip"><span>${escapeHtml(key)}</span><strong>${escapeHtml(value)}</strong></div>`)
          .join('')}
      </div>
    `;

    const brands = Array.isArray(data.brands) ? data.brands : [];
    const brandsSection = document.getElementById('brandsSection');
    const brandsGrid = document.getElementById('brandsGrid');
    const brandsEmpty = document.getElementById('brandsEmpty');
    brandsSection.classList.remove('d-none');
    if (brands.length) {
      brandsEmpty.classList.add('d-none');
      brandsGrid.innerHTML = brands.map(brandCard).join('');
    } else {
      brandsGrid.innerHTML = '';
      brandsEmpty.classList.remove('d-none');
    }

    const tags = Array.isArray(data.tags) ? data.tags : [];
    const tagsSection = document.getElementById('tagsSection');
    const tagsGrid = document.getElementById('tagsGrid');
    const tagsEmpty = document.getElementById('tagsEmpty');
    tagsSection.classList.remove('d-none');
    if (tags.length) {
      tagsEmpty.classList.add('d-none');
      tagsGrid.innerHTML = tags
        .map((tag) => `<a class="btn btn-sm btn-outline-light" href="/browse/hentai-tags/${encodeURIComponent(tag.text)}/0">${escapeHtml(tag.text)} <span class="ms-1 badge text-bg-secondary">${escapeHtml(tag.count ?? 0)}</span></a>`)
        .join('');
    } else {
      tagsGrid.innerHTML = '';
      tagsEmpty.classList.remove('d-none');
    }

    const categories = Array.isArray(data.categories) ? data.categories : [];
    const categoriesSection = document.getElementById('categoriesSection');
    const categoriesGroup = document.getElementById('categoriesGroup');
    const categoriesEmpty = document.getElementById('categoriesEmpty');
    categoriesSection.classList.remove('d-none');

    if (categories.length) {
      categoriesEmpty.classList.add('d-none');
      categoriesGroup.innerHTML = categories
        .map((group) => {
          const items = Array.isArray(group.items) ? group.items : [];
          return `
            <div class="mb-4">
              <h3 class="h6 text-info mb-2">${escapeHtml(group.key)}</h3>
              <div class="browse-grid">
                ${items.map((item) => categoryCard(item, group.key)).join('')}
              </div>
            </div>
          `;
        })
        .join('');
    } else {
      categoriesGroup.innerHTML = '';
      categoriesEmpty.classList.remove('d-none');
    }

    const rawSection = document.getElementById('rawSection');
    const rawJson = document.getElementById('rawJson');
    rawSection.classList.remove('d-none');
    rawJson.textContent = JSON.stringify(data.raw || data, null, 2);
  } catch (err) {
    errorEl.classList.remove('d-none');
    errorEl.innerHTML = `${escapeHtml(err.message)} <button class="btn btn-sm btn-outline-dark ms-2" data-retry-url="/browse">Retry Page</button>`;
    setupRetryButtons();
  } finally {
    loading.classList.add('d-none');
  }
}

function setupBrowsePage() {
  if (!document.querySelector('[data-browse-app]')) return;
  loadBrowseData();

  const refreshButton = document.getElementById('refreshBrowseBtn');
  if (refreshButton) {
    refreshButton.addEventListener('click', () => {
      loadBrowseData(true);
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  setupRetryButtons();
  setupBrowsePage();
});
