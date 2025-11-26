// -----------------------------
// DOM 요소
// -----------------------------
const slides = [
    document.getElementById("slide-meal"),
    document.getElementById("slide-schedule"),
    document.getElementById("slide-notice")
];

let index = 0;

// -----------------------------
// 데이터 로딩
// -----------------------------
async function loadMeal() {
    const res = await fetch("/api/meal");
    const data = await res.json();

    const breakfastList = document.getElementById("meal-breakfast");
    const lunchList     = document.getElementById("meal-lunch");
    const dinnerList    = document.getElementById("meal-dinner");

    breakfastList.innerHTML = "";
    lunchList.innerHTML     = "";
    dinnerList.innerHTML    = "";

    if (data["조식"]) data["조식"].forEach(item => breakfastList.appendChild(createLi(item)));
    else breakfastList.innerHTML = "<li>급식 정보가 없습니다.</li>";

    if (data["중식"]) data["중식"].forEach(item => lunchList.appendChild(createLi(item)));
    else lunchList.innerHTML = "<li>급식 정보가 없습니다.</li>";

    if (data["석식"]) data["석식"].forEach(item => dinnerList.appendChild(createLi(item)));
    else dinnerList.innerHTML = "<li>급식 정보가 없습니다.</li>";
}

async function loadSchedule() {
    const res = await fetch("/api/schedule");
    const data = await res.json();

    const container = document.getElementById("schedule-content");
    let text = "";
    data.forEach(item => text += `${item.date} - ${item.title}\n`);
    container.textContent = text || "일정 정보가 없습니다.";
}

async function loadNotice() {
    const res = await fetch("/api/notice");
    const data = await res.json();

    const container = document.getElementById("notice-content");
    container.innerHTML = "";

    const notices = Array.isArray(data.notices) ? data.notices : [];
    notices.forEach(n => {
        let text;
        if (typeof n === "string") {
            text = n;
        } else if (n && typeof n === "object") {
            text = n.text || n.title || JSON.stringify(n);
        } else {
            text = String(n);
        }
        container.appendChild(createLi(text));
    });
}

// -----------------------------
// 유틸 함수
// -----------------------------
function createLi(text) {
    const li = document.createElement("li");
    li.textContent = text;
    return li;
}

// -----------------------------
// 슬라이드 전환
// -----------------------------
function showSlide(i) {
    slides.forEach((s, idx) => s.classList.toggle("active", idx === i));
}

// -----------------------------
// 초기 로딩 및 10초 간격 전환
// -----------------------------
async function init() {
    await loadMeal();
    await loadSchedule();
    await loadNotice();
    showSlide(0);

    // 10초마다 공지사항만 갱신
    setInterval(loadNotice, 10 * 1000);

    setInterval(() => {
        index = (index + 1) % slides.length;
        showSlide(index);
    }, 5000);
}

init();
