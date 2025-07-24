import { BASE_API_URL } from './config.js';

document.addEventListener('DOMContentLoaded', function() {
    const token = localStorage.getItem("token");
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

    const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    weekdays.forEach(day => {
        const div = document.createElement('div');
        div.textContent = day;
        calendarWeekdaysEl.appendChild(div);
    });

    async function fetchWorkoutPlansForMonth(year, month) {
        const startDate = new Date(year, month, 1);
        const endDate = new Date(year, month + 1, 0); // Last day of the month
        const start = startDate.toISOString().split('T')[0];
        const end = endDate.toISOString().split('T')[0];

        try {
            const response = await fetch(`${BASE_API_URL}/plans/range/${start}/${end}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) {
                throw new Error('운동 계획을 불러오는데 실패했습니다.');
            }

            workoutPlans = await response.json();
            console.log('Fetched workout plans:', workoutPlans); // Debugging: Check fetched data
        } catch (error) {
            console.error('Error fetching workout plans:', error);
            workoutPlans = [];
        }
    }

    function hasWorkoutPlan(date) {
        const formattedDate = date.toISOString().split('T')[0];
        return workoutPlans.some(plan => {
            const planDate = new Date(plan.plan_date + 'T00:00:00'); // 로컬 시간대 자정으로 파싱
            return planDate.getFullYear() === date.getFullYear() &&
                   planDate.getMonth() === date.getMonth() &&
                   planDate.getDate() === date.getDate() &&
                   plan.status !== 'completed'; // completed 상태는 동그라미 표시 안함
        });
    }

    async function fetchMealPlansForDate(date) {
        const formattedDate = date.toISOString().split('T')[0];
        try {
            const response = await fetch(`${BASE_API_URL}/meals/date/${formattedDate}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) {
                throw new Error('식단 계획을 불러오는데 실패했습니다.');
            }

            const mealPlans = await response.json();
            console.log('Fetched meal plans:', mealPlans); // Debugging: Check fetched meal data
            return mealPlans;
        } catch (error) {
            console.error('Error fetching meal plans for date:', error);
            return [];
        }
    }

    async function updateMealItemStatus(mealItemId, isEaten) {
        try {
            const response = await fetch(`${BASE_API_URL}/meals/item/${mealItemId}/status?is_eaten=${isEaten}`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!response.ok) {
                throw new Error('식단 항목 상태 업데이트 실패');
            }
            console.log(`Meal item ${mealItemId} status updated to ${isEaten}`);
            return true;
        } catch (error) {
            console.error('Error updating meal item status:', error);
            return false;
        }
    }

    async function addMealItem(mealPlanId, foodName, calories, protein, carbs, fat) {
        try {
            const response = await fetch(`${BASE_API_URL}/meals/plan/${mealPlanId}/item`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    food_name: foodName,
                    calories: calories,
                    protein: protein,
                    carbs: carbs,
                    fat: fat
                })
            });
            if (!response.ok) {
                throw new Error('식단 항목 추가 실패');
            }
            const newItem = await response.json();
            console.log('New meal item added:', newItem);
            return newItem;
        } catch (error) {
            console.error('Error adding meal item:', error);
            return null;
        }
    }

    async function renderCalendar() {
        calendarGridEl.innerHTML = ''; // Clear previous days
        currentMonthYearEl.textContent = new Date(currentYear, currentMonth).toLocaleString('en-US', { month: 'long', year: 'numeric' });

        await fetchWorkoutPlansForMonth(currentYear, currentMonth);

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
                console.log(`Has workout plan for today: ${hasWorkoutPlan(currentDate)}`); // Debugging: Check hasWorkoutPlan result
            }

            if (hasWorkoutPlan(currentDate)) {
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
        const plansForDate = workoutPlans.filter(plan => {
            const planDate = new Date(plan.plan_date + 'T00:00:00'); // 로컬 시간대 자정으로 파싱
            return planDate.getFullYear() === date.getFullYear() &&
                   planDate.getMonth() === date.getMonth() &&
                   planDate.getDate() === date.getDate();
        });

        if (plansForDate.length > 0) {
            workoutPlanDetails.innerHTML = '<h3>Workout Plan</h3>';
            plansForDate.forEach(plan => {
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
                workoutPlanDetails.innerHTML += `<p>${statusIcon} ${plan.exercise_name} (${plan.sets} sets x ${plan.reps} reps)</p>`;
            });
        } else {
            workoutPlanDetails.innerHTML = '<h3>Workout Plan</h3><p>No workout plan for this date.</p>';
        }

        // Meal plan (dummy data for now)
        mealPlanDetails.innerHTML = '<h3>Meal Plan</h3><p>No meal plan for this date. (To be implemented later)</p>';

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
});