// 🎄 Новорічна тема - JavaScript для динамічних елементів
(function() {
  'use strict';

  const STORAGE_KEY = 'christmasTheme';
  const TOGGLE_ID = 'christmasThemeToggle';

  // Функція для створення сніжинок
  function createSnowflakes() {
    const snowflakeCount = 50;
    const snowflakes = ['❄', '❅', '❆'];
    const body = document.body;

    for (let i = 0; i < snowflakeCount; i++) {
      const snowflake = document.createElement('div');
      snowflake.className = 'snowflake';
      snowflake.textContent = snowflakes[Math.floor(Math.random() * snowflakes.length)];
      snowflake.style.left = Math.random() * 100 + '%';
      snowflake.style.animationDuration = (Math.random() * 3 + 2) + 's';
      snowflake.style.animationDelay = Math.random() * 5 + 's';
      snowflake.style.fontSize = (Math.random() * 0.8 + 0.8) + 'em';
      body.appendChild(snowflake);
    }
  }

  // Функція для створення гірлянди
  function createChristmasLights() {
    const lightsContainer = document.createElement('div');
    lightsContainer.className = 'christmas-lights';
    
    for (let i = 0; i < 15; i++) {
      const light = document.createElement('div');
      light.className = 'light';
      lightsContainer.appendChild(light);
    }
    
    document.body.appendChild(lightsContainer);
  }

  // Гірлянда для навігаційної панелі
  function createDrawerLights() {
    const drawer = document.querySelector('.nav-drawer__panel');
    if (!drawer) return;
    
    const lightsContainer = document.createElement('div');
    lightsContainer.className = 'christmas-drawer-lights';
    
    for (let i = 0; i < 12; i++) {
      const light = document.createElement('div');
      light.className = 'light';
      lightsContainer.appendChild(light);
    }
    
    drawer.appendChild(lightsContainer);
  }

  // Снігова підлога для навігаційної панелі
  function createDrawerSnowFloor() {
    const drawer = document.querySelector('.nav-drawer__panel');
    if (!drawer) return;
    
    const snowFloor = document.createElement('div');
    snowFloor.className = 'christmas-drawer-snow-floor';
    snowFloor.innerHTML = `
      <svg viewBox="0 0 340 120" preserveAspectRatio="none" width="100%" height="120">
        <!-- Снігові сугроби -->
        <path d="M0,60 Q40,45 80,55 Q120,65 160,50 Q200,35 240,50 Q280,60 320,45 Q340,40 340,40 L340,120 L0,120 Z" 
              fill="rgba(241,245,249,0.95)" stroke="rgba(226,232,240,0.5)" stroke-width="1"/>
        <path d="M0,70 Q50,55 100,68 Q150,75 200,62 Q250,50 300,65 Q330,72 340,68" 
              fill="none" stroke="rgba(203,213,225,0.6)" stroke-width="1.5"/>
        <ellipse cx="170" cy="75" rx="140" ry="12" fill="rgba(226,232,240,0.4)"/>
      </svg>
    `;
    drawer.appendChild(snowFloor);
  }

  // Сніговик для навігаційної панелі
  function createDrawerSnowman() {
    const drawer = document.querySelector('.nav-drawer__panel');
    if (!drawer) return;
    
    const snowman = document.createElement('div');
    snowman.className = 'christmas-drawer-snowman';
    snowman.innerHTML = `
      <svg class="snowman-svg" viewBox="0 0 120 170" width="90" height="130">
        
        <!-- Нижня куля -->
        <circle cx="60" cy="130" r="28" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5"/>
        <circle cx="60" cy="130" r="28" fill="url(#snowGradient1)" opacity="0.6"/>
        
        <!-- Середня куля -->
        <circle cx="60" cy="90" r="24" fill="#f8fafc" stroke="#cbd5e1" stroke-width="1.5"/>
        <circle cx="60" cy="90" r="24" fill="url(#snowGradient2)" opacity="0.6"/>
        
        <!-- Гудзики -->
        <circle cx="60" cy="85" r="2.5" fill="#1e293b"/>
        <circle cx="60" cy="93" r="2.5" fill="#1e293b"/>
        <circle cx="60" cy="101" r="2.5" fill="#1e293b"/>
        
        <!-- Голова -->
        <circle cx="60" cy="55" r="20" fill="#ffffff" stroke="#cbd5e1" stroke-width="1.5"/>
        <circle cx="60" cy="55" r="20" fill="url(#snowGradient3)" opacity="0.5"/>
        
        <!-- Очі -->
        <circle cx="53" cy="52" r="2.5" fill="#1e293b"/>
        <circle cx="67" cy="52" r="2.5" fill="#1e293b"/>
        
        <!-- Ніс (морквина) -->
        <path d="M60,58 L75,60 L60,62 Z" fill="#f97316" stroke="#ea580c" stroke-width="0.8"/>
        
        <!-- Посмішка -->
        <path d="M50,63 Q60,68 70,63" fill="none" stroke="#1e293b" stroke-width="2" stroke-linecap="round"/>
        
        <!-- Капелюх -->
        <ellipse cx="60" cy="37" rx="22" ry="3" fill="#1e293b"/>
        <rect x="48" y="20" width="24" height="17" rx="2" fill="#1e293b"/>
        <rect x="48" y="20" width="24" height="3" fill="#dc2626"/>
        
        <!-- Ліва рука -->
        <line x1="36" y1="90" x2="15" y2="80" stroke="#78350f" stroke-width="3" stroke-linecap="round"/>
        <line x1="15" y1="80" x2="8" y2="85" stroke="#78350f" stroke-width="2.5" stroke-linecap="round"/>
        <line x1="15" y1="80" x2="10" y2="74" stroke="#78350f" stroke-width="2.5" stroke-linecap="round"/>
        
        <!-- Права рука (махає) -->
        <g class="snowman-waving-arm">
          <line x1="84" y1="90" x2="105" y2="80" stroke="#78350f" stroke-width="3" stroke-linecap="round"/>
          <line x1="105" y1="80" x2="112" y2="85" stroke="#78350f" stroke-width="2.5" stroke-linecap="round"/>
          <line x1="105" y1="80" x2="110" y2="74" stroke="#78350f" stroke-width="2.5" stroke-linecap="round"/>
        </g>
        
        <!-- Шарф -->
        <ellipse cx="60" cy="73" rx="21" ry="4" fill="#dc2626"/>
        <path d="M70,73 L80,90 L75,92 L72,78" fill="#dc2626"/>
        <path d="M75,90 L78,92 M76,87 L79,89" stroke="#b91c1c" stroke-width="1.5"/>
        
        <!-- Градієнти для об'єму -->
        <defs>
          <radialGradient id="snowGradient1">
            <stop offset="30%" stop-color="#ffffff" stop-opacity="0.8"/>
            <stop offset="100%" stop-color="#cbd5e1" stop-opacity="0.3"/>
          </radialGradient>
          <radialGradient id="snowGradient2">
            <stop offset="30%" stop-color="#ffffff" stop-opacity="0.8"/>
            <stop offset="100%" stop-color="#cbd5e1" stop-opacity="0.3"/>
          </radialGradient>
          <radialGradient id="snowGradient3">
            <stop offset="40%" stop-color="#ffffff" stop-opacity="0.9"/>
            <stop offset="100%" stop-color="#e2e8f0" stop-opacity="0.4"/>
          </radialGradient>
        </defs>
      </svg>
    `;
    
    drawer.appendChild(snowman);
  }

  // Перевірка чи активна новорічна тема
  function isChristmasThemeActive() {
    return localStorage.getItem(STORAGE_KEY) === 'true';
  }

  function setToggleVisualState(isOn) {
    const toggle = document.getElementById(TOGGLE_ID);
    if (!toggle) return;
    toggle.classList.toggle('is-on', isOn);
    toggle.setAttribute('aria-pressed', String(isOn));
  }

  function removeChristmasDecorations() {
    document.querySelectorAll('.snowflake, .christmas-lights, .christmas-banner, .christmas-drawer-lights, .christmas-drawer-snowman, .christmas-drawer-snow-floor').forEach(el => el.remove());
  }

  // Функція для увімкнення новорічної теми
  function enableChristmasTheme() {
    removeChristmasDecorations();
    document.body.classList.add('christmas-theme');
    createSnowflakes();
    createChristmasLights();
    createDrawerLights();
    createDrawerSnowFloor();
    createDrawerSnowman();
    localStorage.setItem(STORAGE_KEY, 'true');
    setToggleVisualState(true);
  }

  // Функція для вимкнення новорічної теми
  function disableChristmasTheme() {
    document.body.classList.remove('christmas-theme');
    removeChristmasDecorations();
    localStorage.setItem(STORAGE_KEY, 'false');
    setToggleVisualState(false);
  }

  // Функція для перемикання теми
  window.toggleChristmasTheme = function() {
    if (isChristmasThemeActive()) {
      disableChristmasTheme();
    } else {
      enableChristmasTheme();
    }
  };

  // Автоматична активація при завантаженні сторінки
  document.addEventListener('DOMContentLoaded', function() {
    const toggle = document.getElementById(TOGGLE_ID);
    if (toggle) {
      toggle.addEventListener('click', function() {
        window.toggleChristmasTheme();
      });
    }

    // Відновлюємо стан тільки якщо користувач раніше вмикав тему
    if (isChristmasThemeActive()) {
      enableChristmasTheme();
    } else {
      setToggleVisualState(false);
    }
  });

  // Музика (опціонально, розкоментуй якщо хочеш)
  /*
  function playChristmasMusic() {
    const audio = new Audio('/static/christmas-music.mp3');
    audio.loop = true;
    audio.volume = 0.3;
    
    // Додати кнопку для керування музикою
    const musicButton = document.createElement('button');
    musicButton.innerHTML = '🎵';
    musicButton.title = 'Новорічна музика';
    musicButton.style.cssText = `
      position: fixed;
      bottom: 140px;
      right: 20px;
      width: 50px;
      height: 50px;
      border-radius: 50%;
      border: none;
      background: #165b33;
      color: white;
      font-size: 20px;
      cursor: pointer;
      z-index: 10000;
    `;
    
    let isPlaying = false;
    musicButton.addEventListener('click', function() {
      if (isPlaying) {
        audio.pause();
        this.innerHTML = '🎵';
      } else {
        audio.play();
        this.innerHTML = '🔇';
      }
      isPlaying = !isPlaying;
    });
    
    document.body.appendChild(musicButton);
  }
  */

})();
