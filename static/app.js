const tabs = document.querySelectorAll(".tab");
const drawerTabs = document.querySelectorAll(".drawer-tab");
const newsList = document.getElementById("newsList");
const updatedAtEl = document.getElementById("updatedAt");

const menuBtn = document.getElementById("menuBtn");
const closeDrawerBtn = document.getElementById("closeDrawerBtn");
const drawer = document.getElementById("sideDrawer");
const backdrop = document.getElementById("backdrop");

let currentTab = "ent";
let dataset = null;

function setDrawerOpen(isOpen) {
  if (!drawer || !backdrop || !menuBtn) return;

  if (isOpen) {
    drawer.classList.add("open");
    drawer.setAttribute("aria-hidden", "false");
    backdrop.hidden = false;
    menuBtn.setAttribute("aria-expanded", "true");
    menuBtn.setAttribute("aria-label", "메뉴 닫기");
    document.body.style.overflow = "hidden";
    return;
  }

  drawer.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
  backdrop.hidden = true;
  menuBtn.setAttribute("aria-expanded", "false");
  menuBtn.setAttribute("aria-label", "메뉴 열기");
  document.body.style.overflow = "";
}

function activateTab(tabKey) {
  tabs.forEach((t) => t.classList.remove("active"));
  const target = Array.from(tabs).find((t) => t.dataset.tab === tabKey);
  if (!target) return;
  target.classList.add("active");
  currentTab = tabKey;
  render();
}

function render() {
  if (!dataset || !dataset.categories || !dataset.categories[currentTab]) {
    newsList.innerHTML = "<li>데이터가 없습니다.</li>";
    return;
  }

  const items = dataset.categories[currentTab].items || [];
  newsList.innerHTML = items
    .map((item) => {
      const thumb = item.thumbnail || "";
      const media = item.media || "출처 미상";
      return `
        <li class="news-item">
          <img class="thumb" src="${thumb}" alt="" loading="lazy" referrerpolicy="no-referrer" />
          <div class="content">
            <div class="rank">${item.rank}위</div>
            <div class="title">
              <a href="${item.url}" target="_blank" rel="noopener noreferrer">${item.title}</a>
            </div>
            <div class="meta">${media}</div>
          </div>
        </li>
      `;
    })
    .join("");
}

async function load() {
  const res = await fetch("/api/rankings");
  if (!res.ok) {
    throw new Error("랭킹 데이터를 가져오지 못했습니다.");
  }
  dataset = await res.json();
  updatedAtEl.textContent = `업데이트: ${dataset.updatedAt}`;
  render();
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    currentTab = tab.dataset.tab;
    render();
  });
});

load().catch((err) => {
  updatedAtEl.textContent = "오류 발생";
  newsList.innerHTML = `<li>${err.message}</li>`;
});

// 드로어(햄버거 메뉴)
menuBtn?.addEventListener("click", () => {
  const isOpen = drawer.classList.contains("open");
  setDrawerOpen(!isOpen);
});

closeDrawerBtn?.addEventListener("click", () => setDrawerOpen(false));
backdrop?.addEventListener("click", () => setDrawerOpen(false));

window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") setDrawerOpen(false);
});

drawerTabs.forEach((btn) => {
  btn.addEventListener("click", () => {
    const key = btn.dataset.tab;
    activateTab(key);
    setDrawerOpen(false);
  });
});
