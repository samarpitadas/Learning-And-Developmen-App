    function showForm(form) {
        const loginForm = document.getElementById('login-form');
        const signupForm = document.getElementById('signup-form');
        const loginTab = document.querySelector('.tab:nth-child(1)');
        const signupTab = document.querySelector('.tab:nth-child(2)');

        if (form === 'login') {
            loginForm.style.display = 'block';
            signupForm.style.display = 'none';
            loginTab.classList.add('active');
            signupTab.classList.remove('active');
        } else {
            loginForm.style.display = 'none';
            signupForm.style.display = 'block';
            loginTab.classList.remove('active');
            signupTab.classList.add('active');
        }
}
