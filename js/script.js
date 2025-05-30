// Smooth scrolling and animations
    document.addEventListener('DOMContentLoaded', function() {

      function toggleMobileMenu() {
        const nav = document.getElementById('nav-menu');
        const btn = document.querySelector('.mobile-menu-btn span');

        nav.classList.toggle('active');

        // Animate the menu button text
        if (btn) {
          if (nav.classList.contains('active')) {
            btn.innerHTML = 'Close ✕';
          } else {
            btn.innerHTML = '☰ Menu';
          }
        }
      }

      // Close mobile menu when clicking on a link
      document.querySelectorAll('#nav-menu a').forEach(link => {
        link.addEventListener('click', () => {
          const nav = document.getElementById('nav-menu');
          const btn = document.querySelector('.mobile-menu-btn span');

          if (nav.classList.contains('active')) {
            nav.classList.remove('active');
            if (btn) btn.innerHTML = '☰ Menu';
          }
        });
      });

      // Close mobile menu when clicking outside
      document.addEventListener('click', (e) => {
        const nav = document.getElementById('nav-menu');
        const btn = document.querySelector('.mobile-menu-btn span');
        const navSection = document.querySelector('.nav-section');

        if (!navSection.contains(e.target) && !e.target.closest('.mobile-menu-btn')) {
          if (nav.classList.contains('active')) {
            nav.classList.remove('active');
            if (btn) btn.innerHTML = '☰ Menu';
          }
        }
      });
      // Intersection Observer for animations
      alert("Hey mate, welcome to the Bishop Abiero Shaurimoyo Secondary School website! We are glad to have you here. The site is still under development, so please bear with us as we work to make it even better. If you have any questions or need assistance, feel free to reach out. Enjoy your visit!");
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
          }
        });
      }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
      });

      // Observe all sections
      document.querySelectorAll('section').forEach(section => {
        observer.observe(section);
      });

      // Header scroll effect
      let lastScroll = 0;
      window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        const header = document.querySelector('header');
        
        if (currentScroll > 100) {
          header.style.background = 'rgba(44, 90, 160, 0.95)';
          header.style.backdropFilter = 'blur(15px)';
        } else {
          header.style.background = 'linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%)';
          header.style.backdropFilter = 'blur(10px)';
        }
        
        lastScroll = currentScroll;
      });
    });
    

    // M-Pesa payment simulation
    function sendMpesaPayment() {
      const form = document.getElementById('supportForm');
      const name = document.getElementById('name').value;
      const phone = document.getElementById('phone').value;
      const amount = document.getElementById('amount').value;
      
      if (!name || !phone || !amount) {
        alert('Please fill in all required fields.');
        return;
      }

      const paymentText = document.getElementById('payment-text');
      const paymentLoading = document.getElementById('payment-loading');
      
      // Show loading state
      paymentText.style.display = 'none';
      paymentLoading.style.display = 'inline-block';
      
      // Simulate payment processing
      setTimeout(() => {
        paymentText.style.display = 'inline';
        paymentLoading.style.display = 'none';
        
        alert(`Thank you ${name}! Your contribution of KES ${amount} is being processed. You will receive an M-Pesa prompt on ${phone} shortly.`);
        form.reset();
      }, 2000);
    }

    const allItems = document.querySelectorAll('.gallery-item');
    const viewMoreBtn = document.getElementById('view-more-btn');
    const filterButtons = document.querySelectorAll('.filter-btn');
    const hiddenItems = document.querySelectorAll('.gallery-item[data-extra]');

    let initialLimit = 6;

    function showInitialItems() {
      allItems.forEach((item, index) => {
        if (index < initialLimit) {
          item.classList.add('show');
        } else {
          item.classList.remove('show');
        }
      });
      viewMoreBtn.style.display = 'block';
    }

    function showAllItems() {
      allItems.forEach(item => item.classList.add('show'));
      viewMoreBtn.style.display = 'none';
    }

    viewMoreBtn.addEventListener('click', showAllItems);
    viewMoreBtn.addEventListener('click', () => {
      const isExpanded = viewMoreBtn.textContent === 'View Less';
      hiddenItems.forEach(item => {
        item.classList.toggle('hidden', isExpanded);
      });

      viewMoreBtn.textContent = isExpanded ? 'View More' : 'View Less';
    });

    // Filter buttons
    filterButtons.forEach(button => {
      button.addEventListener('click', () => {
        const filter = button.getAttribute('data-filter');

        filterButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');

        if (filter === 'all') {
          showInitialItems();
        } else {
          allItems.forEach(item => {
            item.classList.remove('show');
            if (item.classList.contains(filter)) {
              item.classList.add('show');
            }
          });
          viewMoreBtn.style.display = 'none';
        }
      });
    });
    showInitialItems(); // Run once on load


    // Add smooth scrolling to navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
          target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
        }
      });
    });