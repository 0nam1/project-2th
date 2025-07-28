import { BASE_API_URL } from './config.js';

document.addEventListener('DOMContentLoaded', function() {
    const token = sessionStorage.getItem("token");
    if (!token) {
        alert("로그인이 필요합니다.");
        window.location.href = "index.html";
        return;
    }

    const currentMonthYearEl = document.getElementById('currentMonthYear');
    const prevMonthBtn = document.getElementById('prevMonthBtn');
    const nextMonthBtn = document.getElementById('nextMonthBtn');
    const calendarWeekdaysEl = document.getElementById('calendar-weekdays');
    const calendarGridEl = document.getElementById('calendar-grid');
    const detailViewContainer = document.getElementById('detail-view-container');
    const selectedDateDisplay = document.getElementById('selected-date-display');
    const workoutPlanDetails = document.getElementById('workout-plan-details');
    const mealPlanDetails = document.getElementById('meal-plan-details');

    let currentMonth = new Date().getMonth();
    let currentYear = new Date().getFullYear();
    let workoutPlans = []; // 현재 월의 운동 계획을 저장할 배열
    let dietPlans = []; // 현재 월의 식단 계획을 저장할 배열

    const logoutBtn = document.getElementById('logoutBtn'); // 로그아웃 버튼 추가
    const profileBtn = document.getElementById("profileBtn"); // 프로필 버튼 추가
    const modal = document.getElementById("profileModal"); // 프로필 모달 추가
    const profileDetails = document.getElementById("profileDetails"); // 프로필 상세 정보 추가
    const closeModalBtn = document.querySelector(".close"); // 모달 닫기 버튼 추가

    const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    weekdays.forEach(day => {
        const div = document.createElement('div');
        div.textContent = day;
        calendarWeekdaysEl.appendChild(div);
    });

    async function fetchPlansForMonth(year, month) {
        const startDate = new Date(year, month, 1);
        const endDate = new Date(year, month + 1, 0); // Last day of the month
        const start = startDate.toISOString().split('T')[0];
        const end = endDate.toISOString().split('T')[0];

        try {
            const response = await fetch(`${BASE_API_URL}/plans/range/${start}/${end}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) {
                throw new Error('계획을 불러오는데 실패했습니다.');
            }

            const data = await response.json();
            workoutPlans = data.workout_plans || [];
            dietPlans = data.diet_plans || [];
            console.log('Fetched workout plans:', workoutPlans); // Debugging: Check fetched data
            console.log('Fetched diet plans:', dietPlans); // Debugging: Check fetched data
        } catch (error) {
            console.error('Error fetching plans:', error);
            workoutPlans = [];
            dietPlans = [];
        }
    }

    function hasPlan(date) {
        const formattedDate = date.toISOString().split('T')[0];
        const hasWorkout = workoutPlans.some(plan => {
            const planDate = new Date(plan.plan_date + 'T00:00:00'); // 로컬 시간대 자정으로 파싱
            return planDate.getFullYear() === date.getFullYear() &&
                   planDate.getMonth() === date.getMonth() &&
                   planDate.getDate() === date.getDate() &&
                   plan.status !== 'completed'; // completed 상태는 동그라미 표시 안함
        });
        const hasDiet = dietPlans.some(plan => {
            const planDate = new Date(plan.plan_date + 'T00:00:00'); // 로컬 시간대 자정으로 파싱
            return planDate.getFullYear() === date.getFullYear() &&
                   planDate.getMonth() === date.getMonth() &&
                   planDate.getDate() === date.getDate() &&
                   plan.status !== 'completed'; // completed 상태는 동그라미 표시 안함
        });
        return hasWorkout || hasDiet;
    }

    async function renderCalendar() {
        calendarGridEl.innerHTML = ''; // Clear previous days
        currentMonthYearEl.textContent = new Date(currentYear, currentMonth).toLocaleString('en-US', { month: 'long', year: 'numeric' });

        await fetchPlansForMonth(currentYear, currentMonth);

        const firstDayOfMonth = new Date(currentYear, currentMonth, 1).getDay(); // 0 for Sunday, 1 for Monday, etc.
        const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
        const daysInPrevMonth = new Date(currentYear, currentMonth, 0).getDate();

        // Fill leading empty days from previous month
        for (let i = firstDayOfMonth; i > 0; i--) {
            const day = document.createElement('div');
            day.classList.add('calendar-day', 'other-month');
            day.innerHTML = `<span class="day-number">${daysInPrevMonth - i + 1}</span>`;
            calendarGridEl.appendChild(day);
        }

        // Fill days of the current month
        for (let i = 1; i <= daysInMonth; i++) {
            const day = document.createElement('div');
            day.classList.add('calendar-day');
            day.innerHTML = `<span class="day-number">${i}</span>`;

            const currentDate = new Date(currentYear, currentMonth, i);
            if (currentDate.toDateString() === new Date().toDateString()) {
                day.classList.add('today');
                console.log(`Today's date: ${currentDate.toISOString().split('T')[0]}`); // Debugging: Today's date
                console.log(`Has plan for today: ${hasPlan(currentDate)}`); // Debugging: Check hasPlan result
            }

            if (hasPlan(currentDate)) {
                day.classList.add('has-event'); // 일정이 있는 날에 클래스 추가
            }
            console.log(`Day ${i} classList:`, day.classList); // Debugging: Check classList for each day

            day.addEventListener('click', () => showDayDetails(currentDate));
            calendarGridEl.appendChild(day);
        }

        // Fill trailing empty days from next month
        const totalDaysDisplayed = firstDayOfMonth + daysInMonth;
        const remainingCells = 42 - totalDaysDisplayed; // 6 rows * 7 days = 42 cells
        for (let i = 1; i <= remainingCells; i++) {
            const day = document.createElement('div');
            day.classList.add('calendar-day', 'other-month');
            day.innerHTML = `<span class="day-number">${i}</span>`;
            calendarGridEl.appendChild(day);
        }
    }

    async function showDayDetails(date) {
        const formattedDate = date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
        selectedDateDisplay.textContent = `Selected Date: ${formattedDate}`;

        // Fetch and display workout plans for the selected date
        const workoutPlansForDate = workoutPlans.filter(plan => {
            const planDate = new Date(plan.plan_date + 'T00:00:00'); // 로컬 시간대 자정으로 파싱
            return planDate.getFullYear() === date.getFullYear() &&
                   planDate.getMonth() === date.getMonth() &&
                   planDate.getDate() === date.getDate();
        });

        if (workoutPlansForDate.length > 0) {
            workoutPlanDetails.innerHTML = '<h3>운동 루틴</h3>';
            workoutPlansForDate.forEach(plan => {
                let statusIcon = '';
                let statusText = '';
                switch (plan.status) {
                    case 'pending':
                        statusIcon = '<span class="status-icon status-pending"><svg><use href="#icon-circle"></use></svg></span>'; // Empty Circle SVG
                        statusText = 'Pending';
                        break;
                    case 'completed':
                        statusIcon = '<span class="status-icon status-completed"><svg><use href="#icon-check"></use></svg></span>'; // Checkmark SVG
                        statusText = 'Completed';
                        break;
                    case 'skipped':
                        statusIcon = '<span class="status-icon status-skipped"><svg><use href="#icon-x"></use></svg></span>'; // X mark SVG
                        statusText = 'Skipped';
                        break;
                    default:
                        statusIcon = '';
                        statusText = plan.status;
                }
                workoutPlanDetails.innerHTML += `<p>${statusIcon} ${plan.exercise_name} (${plan.sets} 세트 x ${plan.reps} 회)</p>`;
            });
        } else {
            workoutPlanDetails.innerHTML = '<h3>운동 루틴</h3><p>No workout plan for this date.</p>';
        }

        // Fetch and display meal plans for the selected date
        const dietPlansForDate = dietPlans.filter(plan => {
            const planDate = new Date(plan.plan_date + 'T00:00:00'); // 로컬 시간대 자정으로 파싱
            return planDate.getFullYear() === date.getFullYear() &&
                   planDate.getMonth() === date.getMonth() &&
                   planDate.getDate() === date.getDate();
        });

        if (dietPlansForDate.length > 0) {
            mealPlanDetails.innerHTML = '<h3>식단</h3>';

            const mealTypes = {
                '아침': [],
                '점심': [],
                '저녁': [],
                '간식': []
            };

            dietPlansForDate.forEach(plan => {
                mealTypes[plan.meal_type].push(plan);
            });

            for (const type in mealTypes) {
                if (mealTypes[type].length > 0) {
                    mealPlanDetails.innerHTML += `<h4>${type}</h4>`;
                    mealTypes[type].forEach(plan => {
                        let statusIcon = '';
                        let statusText = '';
                        switch (plan.status) {
                            case 'pending':
                                statusIcon = '<span class="status-icon status-pending"><svg><use href="#icon-circle"></use></svg></span>'; // Empty Circle SVG
                                statusText = 'Pending';
                                break;
                            case 'completed':
                                statusIcon = '<span class="status-icon status-completed"><svg><use href="#icon-check"></use></svg></span>'; // Checkmark SVG
                                statusText = 'Completed';
                                break;
                            case 'skipped':
                                statusIcon = '<span class="status-icon status-skipped"><svg><use href="#icon-x"></use></svg></span>'; // X mark SVG
                                statusText = 'Skipped';
                                break;
                            default:
                                statusIcon = '';
                                statusText = plan.status;
                        }
                        mealPlanDetails.innerHTML += `<p>${statusIcon} ${plan.food_name} (칼로리: ${plan.calories || 'N/A'}, 단백질: ${plan.protein_g || 'N/A'}g, 탄수화물: ${plan.carbs_g || 'N/A'}g, 지방: ${plan.fat_g || 'N/A'}g)</p>`;
                    });
                }
            }
        } else {
            mealPlanDetails.innerHTML = '<h3>식단</h3><p>No meal plan for this date.</p>';
        }

        detailViewContainer.classList.add('open'); // Slide in the detail view
    }

    // Close detail view when clicking outside (optional, but good UX)
    document.addEventListener('click', (event) => {
        // Check if the click is outside the detail view and not on a calendar day
        if (!detailViewContainer.contains(event.target) && !event.target.closest('.calendar-day') && detailViewContainer.classList.contains('open')) {
            detailViewContainer.classList.remove('open');
        }
    });


    prevMonthBtn.addEventListener('click', () => {
        currentMonth--;
        if (currentMonth < 0) {
            currentMonth = 11;
            currentYear--;
        }
        renderCalendar();
    });

    nextMonthBtn.addEventListener('click', () => {
        currentMonth++;
        if (currentMonth > 11) {
            currentMonth = 0;
            currentYear++;
        }
        renderCalendar();
    });

    renderCalendar(); // Initial render

    logoutBtn.addEventListener('click', () => {
        sessionStorage.removeItem("token");
        sessionStorage.removeItem("chatHistory"); // chatHistory도 함께 삭제
        window.location.href = "index.html";
    });

    profileBtn.addEventListener("click", async () => {
        try {
            const res = await fetch(`${BASE_API_URL}/protected/me`, {
                headers: { Authorization: `Bearer ${token}` },
            });

            if (!res.ok) throw new Error("사용자 정보를 불러올 수 없습니다.");

            const data = await res.json();
            const user = data.user;

            profileDetails.innerHTML = `
                <div class="info-group"><div class="label">아이디</div><div class="value">${user.user_id}</div></div>
                <div class="info-group"><div class="label">성별</div><div class="value">${user.gender}</div></div>
                <div class="info-group"><div class="label">나이</div><div class="value">${user.age}세</div></div>
                <div class="info-group"><div class="label">키</div><div class="value">${user.height}cm</div></div>
                <div class="info-group"><div class="label">몸무게</div><div class="value">${user.weight}kg</div></div>
                <div class="divider"></div>
                <div class="info-group"><div class="label">운동 수준</div><div class="value">${user.level}</div></div>
                <div class="info-group"><div class="label">부상 부위</div><div class="value">${user.injury_part || "없음"}</div></div>
                <div class="info-group"><div class="label">부상 수준</div><div class="value">${user.injury_level || "없음"}</div></div>
            `;

            modal.classList.remove("hidden");
        } catch (err) {
            alert("내 정보를 불러오는 데 실패했습니다.");
            console.error(err);
        }
    });

    closeModalBtn.addEventListener("click", () => modal.classList.add("hidden"));
    window.addEventListener("click", (e) => {
        if (e.target === modal) modal.classList.add("hidden");
    });
});