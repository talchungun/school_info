const slides = [
    document.getElementById("slide-meal"),
    document.getElementById("slide-schedule"),
    document.getElementById("slide-notice"),
    document.getElementById("slide-dday")
];

let index = 0;

// -----------------------------
// D-Day 데이터 로딩 및 HTML 업데이트
// -----------------------------
async function loadDDay() {
    try {
        const res = await fetch("/api/dday");
        const data = await res.json();
        const container = document.getElementById("dday-content-container");
        
        let htmlContent = '';
        
        if (data.dday_count !== null) {
            const info = data.dday_info;
            const count = data.dday_count;
            
            let ddayText;
            let ddayStyle;
            
            if (count > 0) {
                ddayText = `D - ${count}`;
                ddayStyle = "color: #c62828; font-size: 3em; font-weight: bold;";
            } else if (count === 0) {
                ddayText = "D - DAY!";
                ddayStyle = "color: #28a745; font-size: 3em; font-weight: bold;";
            } else {
                ddayText = `D + ${Math.abs(count)}`;
                ddayStyle = "color: #555; font-size: 2em; font-weight: bold;";
            }

            htmlContent = `
                <div class="dday-counter" style="text-align: center; padding: 20px; background: #fff; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin: 30px auto; max-width: 400px;">
                    <h3 style="color: #016893; margin-bottom: 10px;">${info.target_name}</h3>
                    <p style="${ddayStyle}">${ddayText}</p>
                    <p style="color: #666;">(${info.target_date} 기준)</p>
                </div>
            `;
        } else {
            htmlContent = `
                <div style="text-align: center; padding: 20px;">
                    <p>D-Day 정보가 설정되지 않았습니다.</p>
                </div>
            `;
        }

        container.innerHTML = htmlContent;

    } catch (error) {
        console.error("Failed to load D-Day data:", error);
    }
}

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

async function init() {
    await loadMeal();
    await loadSchedule();
    await loadNotice();
    await loadDDay(); 
    showSlide(0);

    setInterval(() => {
        loadNotice();
        loadDDay(); 
    }, 15 * 1000); 

    setInterval(() => {
        index = (index + 1) % slides.length;
        showSlide(index);
    }, 5000);
}

init();