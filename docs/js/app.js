//------------------------------------------------------
// Configuration
//------------------------------------------------------
const CONFIG = {
  // GitHub Pages base URL
  siteBaseUrl: "https://raw.githubusercontent.com/KakkoiiSaber/arknights_poster_scraper/main",

  // Where images are stored inside the repo
  imageBasePath: "assets",

  // GitHub repo link
  githubRepoUrl: "https://github.com/KakkoiiSaber/arknights_poster_scraper",

  // RAW GitHub download base
  rawBaseUrl: "https://raw.githubusercontent.com/KakkoiiSaber/arknights_poster_scraper/main/assets"
};

//------------------------------------------------------
// Helpers
//------------------------------------------------------
async function fetchJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to fetch ${path}`);
  return res.json();
}

function getQueryParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

function truncate(text, maxLen) {
  if (!text) return "";
  return text.length > maxLen ? text.slice(0, maxLen - 1) + "…" : text;
}

// Find the local filename associated with an external image URL
function findImageKey(imageCache, externalUrl) {
  for (const [key, value] of Object.entries(imageCache)) {
    if (value === externalUrl) return key;
  }
  return null;
}

function makeButton(label, href, className = "btn") {
  const btn = document.createElement("a");
  btn.className = className;
  btn.href = href;
  btn.target = "_blank";
  btn.rel = "noopener noreferrer";
  btn.textContent = label;
  return btn;
}

//------------------------------------------------------
// Page router
//------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;

  if (page === "home") initHomePage();
  else if (page === "category") initCategoryPage();
  else if (page === "detail") initDetailPage();
});

//------------------------------------------------------
// Home page
//------------------------------------------------------
async function initHomePage() {
  const listEl = document.getElementById("category-list");
  const errorEl = document.getElementById("home-error");

  try {
    const categoryData = await fetchJSON("cache/category_cache.json");
    const categories = categoryData.categories || [];

    listEl.innerHTML = "";

    categories.forEach((cat) => {
      const card = document.createElement("a");
      card.className = "category-card";
      card.href = `category.html?category=${encodeURIComponent(cat.name)}`;

      card.innerHTML = `
        <div class="category-name">${cat.name}</div>
        <div class="category-count">${cat.count} 张图片</div>
        <div class="category-pill-row">
          <span class="category-pill">点击查看相册</span>
          <span class="category-pill">自动生成</span>
        </div>
      `;
      listEl.appendChild(card);
    });

    if (categories.length === 0) {
      errorEl.hidden = false;
      errorEl.textContent = "未找到任何分类。";
    }
  } catch (err) {
    console.error(err);
    errorEl.hidden = false;
    errorEl.textContent = "无法加载分类列表。";
  }
}

//------------------------------------------------------
// Category Page
//------------------------------------------------------
async function initCategoryPage() {
  const categoryName = getQueryParam("category");
  const titleEl = document.getElementById("category-title");
  const metaEl = document.getElementById("category-meta");
  const galleryEl = document.getElementById("gallery");
  const errorEl = document.getElementById("category-error");

  if (!categoryName) {
    errorEl.hidden = false;
    errorEl.textContent = "未指定分类。";
    return;
  }

  titleEl.textContent = categoryName;

  try {
    const [metaData, categoryData, imageCache] = await Promise.all([
      fetchJSON("cache/meta_cache.json"),
      fetchJSON("cache/category_cache.json"),
      fetchJSON("cache/image_cache.json")
    ]);

    const posters = metaData.posters || [];
    const categories = categoryData.categories || [];

    const thisCategory = categories.find((c) => c.name === categoryName);
    metaEl.textContent = thisCategory ? `共 ${thisCategory.count} 张图片` : "";

    galleryEl.innerHTML = "";
    let count = 0;

    posters.forEach((poster, index) => {
      if (poster.category !== categoryName) return;

      count++;

      const externalUrl = poster.images?.[0] || "";
      const key = findImageKey(imageCache, externalUrl);

      // **Critical fix: encode filename**
      const encodedKey = key ? encodeURIComponent(key) : null;

      // Build final thumbnail URL
      const imageUrl = encodedKey
        ? `${CONFIG.siteBaseUrl}/${CONFIG.imageBasePath}/${encodedKey}`
        : externalUrl;

      const year = poster.year || "";
      const title = poster.title || "";
      const desc = poster.description || "";

      const card = document.createElement("a");
      card.className = "image-card";
      card.href = `detail.html?id=${index}`;

      card.innerHTML = `
        <div class="image-thumb-wrapper">
          <div class="image-thumb">
            <img src="${imageUrl}" loading="lazy" alt="${title}">
          </div>
          <div class="image-badge">${count}</div>
          ${year ? `<div class="image-year">${year}</div>` : ""}
        </div>
        <div class="image-card-body">
          <p class="image-title">${title}</p>
        </div>
      `;
        //   <p class="image-desc">${truncate(desc, 50)}</p>

      galleryEl.appendChild(card);
    });

    if (count === 0) {
      errorEl.hidden = false;
      errorEl.textContent = "该分类没有图片。";
    }

  } catch (err) {
    console.error(err);
    errorEl.hidden = false;
    errorEl.textContent = "加载图片失败。";
  }
}

//------------------------------------------------------
// Detail Page
//------------------------------------------------------
async function initDetailPage() {
  const idStr = getQueryParam("id");
  const detailSection = document.getElementById("detail");
  const errorEl = document.getElementById("detail-error");

  const id = parseInt(idStr, 10);
  if (isNaN(id)) {
    errorEl.hidden = false;
    errorEl.textContent = "无效的图片 ID。";
    return;
  }

  try {
    const [metaData, imageCache] = await Promise.all([
      fetchJSON("cache/meta_cache.json"),
      fetchJSON("cache/image_cache.json")
    ]);

    const posters = metaData.posters || [];
    if (id < 0 || id >= posters.length) {
      errorEl.hidden = false;
      errorEl.textContent = "图片 ID 超出范围。";
      return;
    }

    const poster = posters[id];
    const externalUrl = poster.images?.[0] || "";

    const key = findImageKey(imageCache, externalUrl);
    const encodedKey = key ? encodeURIComponent(key) : null;

    // **Final displayed image**
    const imageUrl = encodedKey
      ? `${CONFIG.siteBaseUrl}/${CONFIG.imageBasePath}/${encodedKey}`
      : externalUrl;

    // RAW download image
    const rawUrl = encodedKey
      ? `${CONFIG.rawBaseUrl}/${encodedKey}`
      : "";

    const title = poster.title || "";
    const desc = poster.description || "";
    const category = poster.category || "";
    const year = poster.year || "";
    const weiboUrl = poster.weibo_url || "";

    document.getElementById("detail-title").textContent = title;

    detailSection.innerHTML = `
      <div class="detail-image-panel">
        <img src="${imageUrl}" alt="${title}">
      </div>

      <div class="detail-meta-panel">
        <h2 class="detail-title">${title}</h2>

        <div class="detail-tags">
          ${category ? `<span class="detail-tag">${category}</span>` : ""}
          ${year ? `<span class="detail-tag">${year}</span>` : ""}
        </div>

        <p class="detail-desc">${desc || "（无描述）"}</p>

        <div class="button-row" id="detail-buttons"></div>
      </div>
    `;

    const buttonRow = document.getElementById("detail-buttons");

    if (weiboUrl)
    //   buttonRow.appendChild(makeButton("在微博查看", weiboUrl, "btn btn-primary"));
      buttonRow.appendChild(makeButton("在微博查看", weiboUrl, "btn"));

    if (rawUrl)
      buttonRow.appendChild(makeButton("下载高清原图", rawUrl, "btn"));

    // buttonRow.appendChild(
    //   makeButton("查看 GitHub 代码", CONFIG.githubRepoUrl, "btn")
    // );

  } catch (err) {
    console.error(err);
    errorEl.hidden = false;
    errorEl.textContent = "加载详情失败。";
  }
}