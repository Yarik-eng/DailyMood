// Підтримувані мови
const SUPPORTED_LANGUAGES = ['uk', 'en'];

// Поточна мова
let currentLanguage = localStorage.getItem('dailyMoodLanguage') || 'uk';

// Функція зміни мови
function changeLanguage(lang) {
    if (!SUPPORTED_LANGUAGES.includes(lang)) return;
    
    const langSelect = document.getElementById('languageSelect');
    if (langSelect) {
        langSelect.classList.add('changing');
        langSelect.setAttribute('value', lang);
// Підтримувані мови
// Поточна мова
        langSelect.value = lang;
        
        // Видаляємо клас після завершення анімації
        setTimeout(() => {
            langSelect.classList.remove('changing');
        }, 300);
    }
    
    currentLanguage = lang;
    localStorage.setItem('dailyMoodLanguage', lang);
    
    // Плавна зміна прозорості для анімації
    document.body.style.opacity = '0.8';
    
    setTimeout(() => {
        // Оновлюємо всі елементи з атрибутом data-i18n
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = currentLanguage === 'uk' ? translations_uk[key] : translations_en[key];
            
            if (translation) {
                if (element.hasAttribute('placeholder')) {
                    element.setAttribute('placeholder', translation);
                } else {
                    element.textContent = translation;
                }
});
        
        document.body.style.opacity = '1';
    }, 150);

    // Викликаємо подію для сповіщення інших скриптів
    window.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: lang } }));
}

// Ініціалізація при завантаженні
document.addEventListener('DOMContentLoaded', () => {
    const langSelect = document.getElementById('languageSelect');
    if (langSelect) {
        langSelect.value = currentLanguage;
        // Застосовуємо переклади одразу без анімації
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = currentLanguage === 'uk' ? translations_uk[key] : translations_en[key];
            if (translation) {
                if (element.hasAttribute('placeholder')) {
                    element.setAttribute('placeholder', translation);
                } else {
                    element.textContent = translation;
                }
            }
        });

        // Додаємо обробник події для зміни мови
        langSelect.addEventListener('change', (e) => {
            changeLanguage(e.target.value);
        });
    }
});