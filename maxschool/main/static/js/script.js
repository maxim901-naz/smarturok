


// Функция открытия модального окна
function openModal(id) {
    let modal = document.getElementById(id);
    modal.classList.remove("hidden");
    modal.classList.add("show", "flex"); // Делаем окно видимым
}

// Функция закрытия модального окна
function closeModal(id) {
    let modal = document.getElementById(id);
    modal.classList.remove("show","flex");
    setTimeout(() => modal.classList.add("hidden"), 200); // Задержка для анимации
}

    // Загружаем анимацию
    lottie.loadAnimation({
        container: document.getElementById('animated-phone'),
        renderer: 'svg',
        loop: true,
        autoplay: true,
        path: '/static/animations/Animationphone.json' // Подставь сюда свой файл с анимацией
    });

    function closeCallbackBox1() {
        let box = document.getElementById("callback-box");
        box.classList.add("opacity-0", "scale-95");
        setTimeout(() => {
            box.classList.add("hidden");
        }, 300);
        setTimeout(() => {
            box.classList.remove("hidden", "opacity-0", "scale-95");
        }, 60000);
    }

    // Плавное появление при загрузке
    document.addEventListener("DOMContentLoaded", function () {
        setTimeout(() => {
            let box = document.getElementById("callback-box");
            box.classList.remove("opacity-0", "scale-95");
        }, 500);
    });

    document.getElementById("callback-form").addEventListener("submit", function(event) {
        event.preventDefault();
        let phone = document.getElementById("phone-input").value;

        if (phone.trim() === "") {
            alert("Введите номер телефона!");
            return;
        }

        alert("Спасибо! Мы вам скоро перезвоним.");
        document.getElementById("phone-input").value = ""; // Очищаем поле после отправки
    });




    function showCallbackBox() {
        let box = document.getElementById("callback-box1");
        box.classList.remove("hidden");
        setTimeout(() => {
            box.querySelector(".relative").classList.add("scale-100");
        }, 50);
    }

    function closeCallbackBox() {
        let box = document.getElementById("callback-box1");
        box.querySelector(".relative").classList.remove("scale-100");
        setTimeout(() => {
            box.classList.add("hidden");
        }, 200);
    }

    document.addEventListener("DOMContentLoaded", function () {
        setTimeout(showCallbackBox, 20000); // Первое появление через 10 сек
        setInterval(showCallbackBox, 40000); // Дальше каждые 30 секунд
    });

    document.getElementById("signup-link").href = "https://example.com"; // Замени на свою ссылку
    // Скрипт для меню и окон -->
    
        document.addEventListener("click", function(event) {
            let menu = document.getElementById("mobile-menu");
            let burgerBtn = document.getElementById("burger-btn");
    
            // Если клик не по кнопке и не по меню — скрываем меню
            if (!menu.classList.contains("hidden") && !menu.contains(event.target) && !burgerBtn.contains(event.target)) {
                menu.classList.add("hidden");
            }
        });
    
        document.getElementById("burger-btn").addEventListener("click", function(event) {
            let menu = document.getElementById("mobile-menu");
            menu.classList.toggle("hidden");
            event.stopPropagation(); // Останавливаем всплытие, чтобы клик не закрыл меню сразу
        });
        //Скрипт для скрытия плавающего окна
    function closeFloatingChat() {
        document.getElementById("floating-chat").style.display = "none";
    }
    // document.addEventListener("DOMContentLoaded", function() {
    //     new Swiper('.swiper-container', {
    //         slidesPerView: 1,
    //         spaceBetween: 20,
    //         loop: true,
    //         autoplay: { delay: 3000 },
    //         pagination: { el: '.swiper-pagination', clickable: true }
    //     });
    // });
    // document.addEventListener("DOMContentLoaded", function() {
    //     AOS.init();
    // });
    // для кабинета учен
    document.addEventListener("DOMContentLoaded", () => {
        // Имитация загрузки данных
        const userData = {
            username: "Максим",
            completedLessons: 12,
            upcomingLessons: 3
        };
    
        // Установка значений в интерфейсе
        document.getElementById("username").textContent = userData.username;
        document.getElementById("completed-lessons").textContent = userData.completedLessons;
        document.getElementById("upcoming-lessons").textContent = userData.upcomingLessons;
    });
    document.addEventListener("DOMContentLoaded", () => {
        // Данные учителя (можно получать с сервера)
        const teacherData = {
            name: "Анна",
            lessonsTaught: 25,
            studentsCount: 8
        };
    
        // Заполняем интерфейс
        document.getElementById("teacher-name").textContent = teacherData.name;
        document.getElementById("lessons-taught").textContent = teacherData.lessonsTaught;
        document.getElementById("students-count").textContent = teacherData.studentsCount;
    });
        