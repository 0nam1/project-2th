// js/auth.js

document.addEventListener("DOMContentLoaded", () => {
  const signupForm = document.getElementById("signup-form");
  const loginForm = document.getElementById("login-form");

  // 회원가입 폼 제출 처리
  if (signupForm) {
    signupForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      const formData = new FormData(this);

      const data = {
        user_id: formData.get("user_id"),
        gender: formData.get("gender"),
        age: parseInt(formData.get("age")),
        height: parseFloat(formData.get("height")),
        weight: parseFloat(formData.get("weight")),
        level: parseInt(formData.get("level")),
        injury_level: formData.get("injury"),
        injury_part: formData.get("injury"),
      };

      try {
        const response = await fetch("http://localhost:8000/users/signup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const error = await response.json();
          alert(error.detail || "회원가입 중 오류 발생");
          return;
        }

        const result = await response.json();
        alert(result.message || "가입 완료!");
        // ✅ JWT 토큰 저장
        localStorage.setItem("token", result.access_token);

        // ✅ 메인 페이지로 이동
        window.location.href = "main.html";
      } catch (err) {
        alert("회원가입 중 오류 발생");
        console.error(err);
      }
    });
  }

  // 로그인 폼 제출 처리
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const user_id = document.getElementById("user_id").value;

      try {
        const res = await fetch("http://localhost:8000/users/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id }),
        });

        const message = document.getElementById("login-message");

        if (res.ok) {
          const data = await res.json();
          message.textContent = data.message;
          message.style.color = "green";

          // 토큰 저장
          localStorage.setItem("token", data.access_token);

          // 메인 페이지로 이동
          window.location.href = "main.html";
        } else {
          const error = await res.json();
          message.textContent = error.detail;
          message.style.color = "red";
        }
      } catch (err) {
        alert("로그인 중 오류 발생");
        console.error(err);
      }
    });
  }
});