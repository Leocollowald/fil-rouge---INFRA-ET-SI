// Burger menu
const burger = document.getElementById('burger-btn');
if (burger) {
  burger.addEventListener('click', () => {
    const expanded = burger.getAttribute('aria-expanded') === 'true';
    burger.setAttribute('aria-expanded', String(!expanded));
    document.querySelector('.navbar__links')?.classList.toggle('open');
    document.querySelector('.navbar__actions')?.classList.toggle('open');
  });
}

// Gestion de l'état auth dans la navbar
const user = JSON.parse(localStorage.getItem('yplaza_user') || 'null');

if (user) {
  document.getElementById('btn-login')?.classList.add('hidden');
  document.getElementById('btn-register')?.classList.add('hidden');
  document.getElementById('user-menu')?.classList.remove('hidden');
}

// Déconnexion
document.getElementById('btn-logout')?.addEventListener('click', async () => {
  await fetch('/api/v1/auth/logout', { method: 'POST' });
  localStorage.removeItem('yplaza_user');
  localStorage.removeItem('yplaza_token');
  window.location.href = '/';
});

// Navbar transparente sur hero (page d'accueil uniquement)
if (document.querySelector('.hero')) {
  const navbar = document.querySelector('.navbar');
  navbar.classList.add('navbar--hero');
  const onScroll = () => {
    navbar.classList.toggle('navbar--scrolled', window.scrollY > 60);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

// Apparition des éléments au scroll
const observer = new IntersectionObserver(
  (entries) => entries.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('visible'); observer.unobserve(e.target); }
  }),
  { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
);
document.querySelectorAll('.property-card, .service-card, .agency-card')
  .forEach(el => observer.observe(el));

// Toggle favori (global, utilisé dans plusieurs pages)
async function toggleFavorite(btn) {
  const token = localStorage.getItem('yplaza_token');
  if (!token) {
    window.location.href = '/connexion';
    return;
  }

  const propertyId = btn.dataset.id;
  try {
    const res = await fetch(`/api/v1/properties/${propertyId}/favorite`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });

    if (res.status === 401) { window.location.href = '/connexion'; return; }

    const data = await res.json();
    btn.classList.toggle('btn-favorite--active', data.is_favorite);
    btn.setAttribute('aria-label', data.is_favorite ? 'Retirer des favoris' : 'Ajouter aux favoris');
  } catch {
    console.error('Erreur favori');
  }
}
