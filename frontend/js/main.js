document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");
  console.log("[INIT] token:", token);

  if (!token) {
    alert("로그인이 필요합니다.");
    window.location.href = "index.html";
    return;
  }

  const chatBox = document.getElementById("chat-box");
  const userInput = document.getElementById("userInput");
  const imageInput = document.getElementById("imageInput");
  const previewWrapper = document.getElementById("imagePreviewWrapper");
  const previewImage = document.getElementById("previewImage");
  const chatForm = document.getElementById("chat-form");

  const profileBtn = document.getElementById("profileBtn");
  const logoutBtn = document.getElementById("logoutBtn");
  const modal = document.getElementById("profileModal");
  const profileDetails = document.getElementById("profileDetails");
  const closeModalBtn = document.querySelector(".close");

  const modelSelector = document.getElementById("modelSelector");

  function appendMessage(sender, text) {
    const msg = document.createElement("div");
    msg.className = `message ${sender}`;
    msg.innerText = text;
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  imageInput.addEventListener("change", () => {
    const file = imageInput.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        previewImage.src = reader.result;
        previewWrapper.classList.add("show");
        console.log("[IMG] 미리보기 이미지 show");
      };
      reader.readAsDataURL(file);
    } else {
      previewImage.src = "";
      previewWrapper.classList.remove("show");
      console.log("[IMG] 미리보기 이미지 hide");
    }
  });

  async function sendMessage(event) {
    event.preventDefault();
    console.log("[sendMessage] 실행");

    const message = userInput.value.trim();
    const file = imageInput.files[0];
    console.log("[sendMessage] message:", message, "file:", file);

    if (!message && !file) return;

    appendMessage("user", message || "[이미지 전송]");
    userInput.value = "";

    const formData = new FormData();
    formData.append("message", message);
    if (file) formData.append("image", file);

    const model = modelSelector.value;
    formData.append("model", model);

    const botMessageDiv = document.createElement("div");
    botMessageDiv.className = "message bot";
    chatBox.appendChild(botMessageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;

    // YouTube 영상을 표시할 컨테이너 추가
    const youtubeVideosContainer = document.createElement("div");
    youtubeVideosContainer.className = "youtube-videos-container";
    chatBox.appendChild(youtubeVideosContainer); // 챗봇 메시지 아래에 추가

    let fullStreamBuffer = ""; // 전체 스트림 데이터를 저장할 버퍼

    try {
      console.log("[sendMessage] /chat/image로 fetch 시작");
      const res = await fetch("/chat/image", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      console.log("[sendMessage] /chat/image 응답:", res.status);

      if (res.ok) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          let chunk = decoder.decode(value, { stream: true });
          botMessageDiv.textContent += chunk;
          fullStreamBuffer += chunk; // 모든 청크를 버퍼에 추가
          chatBox.scrollTop = chatBox.scrollHeight;
        }

        console.log("[sendMessage] 전체 챗봇 응답:", fullStreamBuffer);

        // 스트리밍 완료 후 YouTube 검색
        try {
          console.log("[sendMessage] 유튜브 검색 fetch", fullStreamBuffer);
          const youtubeSearchRes = await fetch(
            `/youtube_search?query=${encodeURIComponent(
              fullStreamBuffer
            )}`,
            {
              headers: { Authorization: `Bearer ${token}` },
            }
          );

          console.log("[sendMessage] 유튜브 검색 응답", youtubeSearchRes.status);

          if (youtubeSearchRes.ok) {
            const videoData = await youtubeSearchRes.json();
            console.log("[sendMessage] 유튜브 videoData", videoData);

            if (videoData && videoData.length > 0) {
              videoData.forEach((video) => {
                const iframe = document.createElement("iframe");
                iframe.width = "100%";
                iframe.height = "200"; // 적절한 높이 설정
                iframe.src = `https://www.youtube.com/embed/${video.id}`;
                iframe.frameBorder = "0";
                iframe.allow =
                  "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
                iframe.allowFullscreen = true;
                youtubeVideosContainer.appendChild(iframe);

                const videoTitle = document.createElement("p");
                videoTitle.innerText = video.title;
                videoTitle.style.fontSize = "0.9em";
                videoTitle.style.marginTop = "5px";
                videoTitle.style.marginBottom = "15px";
                youtubeVideosContainer.appendChild(videoTitle);
              });
            }
          } else {
            console.error(
              "[sendMessage] Failed to fetch YouTube videos:",
              youtubeSearchRes.status,
              youtubeSearchRes.statusText
            );
          }
        } catch (youtubeErr) {
          console.error("[sendMessage] Error fetching YouTube videos:", youtubeErr);
        }

        // TTS
        console.log("[sendMessage] playTTS 호출 직전");
        await playTTS(fullStreamBuffer);
        console.log("[sendMessage] playTTS 호출 후");
      } else {
        botMessageDiv.innerText = "❗ 오류가 발생했습니다.";
        console.error("[sendMessage] /chat/image 오류", res.status);
      }
    } catch (err) {
      botMessageDiv.innerText = "❗ 네트워크 오류입니다.";
      console.error("[sendMessage] 네트워크 오류", err);
    }

    imageInput.value = "";
    previewImage.src = "";
    previewWrapper.classList.remove("show");
  }

  chatForm.addEventListener("submit", sendMessage);

  logoutBtn.addEventListener("click", () => {
    localStorage.removeItem("token");
    window.location.href = "index.html";
    console.log("[로그아웃] token 제거 후 index.html 이동");
  });

  profileBtn.addEventListener("click", async () => {
    try {
      const res = await fetch("/protected/me", {
        headers: { Authorization: `Bearer ${token}` },
      });

      console.log("[프로필] me 호출 응답", res.status);

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
      console.log("[프로필] 프로필 모달 표시");
    } catch (err) {
      alert("내 정보를 불러오는 데 실패했습니다.");
      console.error("[프로필] 내 정보 조회 오류", err);
    }
  });

  closeModalBtn.addEventListener("click", () => {
    modal.classList.add("hidden");
    console.log("[프로필] 모달 닫힘(클릭)");
  });
  window.addEventListener("click", (e) => {
    if (e.target === modal) {
      modal.classList.add("hidden");
      console.log("[프로필] 모달 닫힘(백그라운드 클릭)");
    }
  });
  // TTS 요청 및 오디오 재생 함수(진단용 로그 추가)
  async function playTTS(text) {
    console.log("[playTTS] 호출됨. text:", text);
    try {
      const ttsRes = await fetch("/tts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ text }),
      });
      console.log("[playTTS] fetch 응답 status:", ttsRes.status);
      if (ttsRes.ok) {
        const arrayBuffer = await ttsRes.arrayBuffer();
        console.log("[playTTS] wav 파일 길이(byte):", arrayBuffer.byteLength);

        const blob = new Blob([arrayBuffer], { type: "audio/wav" });
        const audioUrl = URL.createObjectURL(blob);
        console.log("[playTTS] audioUrl:", audioUrl);

        const audio = new Audio(audioUrl);

        audio.oncanplaythrough = () => {
          console.log("[playTTS] 오디오 재생 준비됨. 재생 시작!");
        };
        audio.onended = () => {
          console.log("[playTTS] 오디오 재생 끝!");
        };
        audio.onerror = (e) => {
          console.error("[playTTS] 오디오 에러", e);
        };

        // 실제 재생 시도
        try {
          await audio.play();
          console.log("[playTTS] audio.play() 실행됨");
        } catch (playErr) {
          console.error("[playTTS] audio.play() 에러:", playErr);
        }
      } else {
        console.error("[playTTS] TTS audio fetch error", ttsRes.status);
      }
    } catch (err) {
      console.error("[playTTS] TTS fetch/play error", err);
    }
  }
});





// async function playTTS(text) {
//   console.log("[playTTS] 호출됨. text:", text);
//   try {
//     // 토큰 사용 여부 결정
//     let headers = { "Content-Type": "application/json" };
//     if (typeof token !== 'undefined' && token) {
//       headers["Authorization"] = `Bearer ${token}`;
//     }

//     const ttsRes = await fetch("/tts", {
//       method: "POST",
//       headers,
//       body: JSON.stringify({ text }),
//     });
//     console.log("[playTTS] fetch 응답 status:", ttsRes.status);
//     if (ttsRes.ok) {
//       const arrayBuffer = await ttsRes.arrayBuffer();
//       console.log("[playTTS] wav 파일 길이(byte):", arrayBuffer.byteLength);

//       const blob = new Blob([arrayBuffer], { type: "audio/wav" });
//       const audioUrl = URL.createObjectURL(blob);
//       console.log("[playTTS] audioUrl:", audioUrl);

//       const audio = new Audio(audioUrl);

//       audio.oncanplaythrough = () => {
//         console.log("[playTTS] 오디오 재생 준비됨. 재생 시작!");
//       };
//       audio.onended = () => {
//         console.log("[playTTS] 오디오 재생 끝!");
//       };
//       audio.onerror = (e) => {
//         console.error("[playTTS] 오디오 에러", e);
//       };

//       // 실제 재생 시도
//       try {
//         await audio.play();
//         console.log("[playTTS] audio.play() 실행됨");
//       } catch (playErr) {
//         console.error("[playTTS] audio.play() 에러:", playErr);
//       }
//     } else {
//       console.error("[playTTS] TTS audio fetch error", ttsRes.status);
//     }
//   } catch (err) {
//     console.error("[playTTS] TTS fetch/play error", err);
//   }
// }

