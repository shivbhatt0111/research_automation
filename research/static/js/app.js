// Navbar Component
const Navbar = {
  render() {
      return `
          <nav class="bg-white shadow-sm border-b border-slate-200 sticky top-0 z-50">
              <div class="container mx-auto px-4">
                  <div class="flex justify-between items-center h-16">
                      <!-- Logo -->
                      <div class="flex items-center space-x-2">
                          <div class="bg-primary p-2 rounded-lg">
                              <i class="fas fa-search text-white text-xl"></i>
                          </div>
                          <div>
                              <h1 class="text-xl font-bold text-slate-800">Research Automation</h1>
                              <p class="text-xs text-slate-500">Intelligent Company Discovery</p>
                          </div>
                      </div>

                      <!-- Navigation Links -->
                      <div class="hidden md:flex items-center space-x-8">
                          <a href="#" class="text-primary font-medium border-b-2 border-primary pb-1">
                              <i class="fas fa-home mr-2"></i>Dashboard
                          </a>
                          <a href="#features" class="text-slate-600 hover:text-primary transition-colors">
                              <i class="fas fa-star mr-2"></i>Features
                          </a>
                      </div>

                      <!-- Action Button -->
                      <div class="flex items-center space-x-3">
                          <button onclick="showNewResearchModal()" 
                                  class="bg-primary hover:bg-indigo-700 text-white px-5 py-2.5 rounded-lg font-medium transition-all shadow-lg shadow-indigo-500/30 flex items-center space-x-2">
                              <i class="fas fa-plus-circle"></i>
                              <span>New Research</span>
                          </button>
                      </div>
                  </div>
              </div>
          </nav>
      `;
  }
};

// Home Component
const Home = {
  render() {
      return `
          <!-- Hero Section -->
          <section class="mb-16 animate-fade-in">
              <div class="bg-gradient-to-br from-indigo-600 via-indigo-700 to-purple-800 rounded-2xl p-12 text-white shadow-2xl">
                  <div class="max-w-4xl mx-auto text-center">
                      <div class="mb-6">
                          <span class="bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full text-sm font-medium">
                              <i class="fas fa-bolt mr-2"></i>AI-Powered Research
                          </span>
                      </div>
                      <h1 class="text-4xl md:text-5xl font-bold mb-6 leading-tight">
                          Discover Companies <br/>
                          <span class="text-indigo-200">In Minutes, Not Hours</span>
                      </h1>
                      <p class="text-lg md:text-xl text-indigo-100 mb-8 max-w-2xl mx-auto">
                          Automated company research with verified contact details, 
                          key decision-makers, and intelligent data extraction.
                      </p>
                      <div class="flex flex-col sm:flex-row justify-center space-y-4 sm:space-y-0 sm:space-x-4">
                          <button onclick="showNewResearchModal()" 
                                  class="bg-white text-indigo-700 px-8 py-4 rounded-xl font-bold text-lg hover:bg-indigo-50 transition-all shadow-xl">
                              <i class="fas fa-rocket mr-2"></i>Start Research
                          </button>
                          <button onclick="scrollToFeatures()" 
                                  class="bg-indigo-800/50 backdrop-blur-sm text-white px-8 py-4 rounded-xl font-bold text-lg hover:bg-indigo-800/70 transition-all border border-indigo-400">
                              <i class="fas fa-play-circle mr-2"></i>Learn More
                          </button>
                      </div>
                  </div>
              </div>
          </section>

          <!-- Stats Section -->
          <section class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-16">
              <div class="bg-white p-6 rounded-xl shadow-lg border border-slate-200 hover:-translate-y-1 transition-transform duration-300">
                  <div class="flex items-center justify-between mb-4">
                      <div class="bg-blue-100 p-3 rounded-lg">
                          <i class="fas fa-building text-blue-600 text-2xl"></i>
                      </div>
                      <span class="text-3xl font-bold text-slate-800">10K+</span>
                  </div>
                  <p class="text-slate-600 font-medium">Companies Researched</p>
              </div>
              
              <div class="bg-white p-6 rounded-xl shadow-lg border border-slate-200 hover:-translate-y-1 transition-transform duration-300">
                  <div class="flex items-center justify-between mb-4">
                      <div class="bg-green-100 p-3 rounded-lg">
                          <i class="fas fa-envelope text-green-600 text-2xl"></i>
                      </div>
                      <span class="text-3xl font-bold text-slate-800">85%</span>
                  </div>
                  <p class="text-slate-600 font-medium">Email Accuracy</p>
              </div>
              
              <div class="bg-white p-6 rounded-xl shadow-lg border border-slate-200 hover:-translate-y-1 transition-transform duration-300">
                  <div class="flex items-center justify-between mb-4">
                      <div class="bg-purple-100 p-3 rounded-lg">
                          <i class="fas fa-clock text-purple-600 text-2xl"></i>
                      </div>
                      <span class="text-3xl font-bold text-slate-800">5 Min</span>
                  </div>
                  <p class="text-slate-600 font-medium">Avg. Research Time</p>
              </div>
              
              <div class="bg-white p-6 rounded-xl shadow-lg border border-slate-200 hover:-translate-y-1 transition-transform duration-300">
                  <div class="flex items-center justify-between mb-4">
                      <div class="bg-orange-100 p-3 rounded-lg">
                          <i class="fas fa-check-circle text-orange-600 text-2xl"></i>
                      </div>
                      <span class="text-3xl font-bold text-slate-800">98%</span>
                  </div>
                  <p class="text-slate-600 font-medium">Data Verification</p>
              </div>
          </section>

          <!-- Features Section -->
          <section id="features" class="mb-16 scroll-mt-20">
              <div class="text-center mb-12">
                  <h2 class="text-3xl md:text-4xl font-bold text-slate-800 mb-4">Powerful Features</h2>
                  <p class="text-slate-600 text-lg max-w-2xl mx-auto">
                      Everything you need for comprehensive company research and lead generation
                  </p>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                  <!-- Feature 1 -->
                  <div class="bg-white p-8 rounded-xl shadow-lg border border-slate-200 hover:shadow-xl transition-shadow">
                      <div class="bg-indigo-100 w-14 h-14 rounded-xl flex items-center justify-center mb-6">
                          <i class="fas fa-search text-primary text-2xl"></i>
                      </div>
                      <h3 class="text-xl font-bold text-slate-800 mb-3">Smart Discovery</h3>
                      <p class="text-slate-600 leading-relaxed">
                          AI-powered search to find companies by industry, location, and specific criteria with verified websites.
                      </p>
                  </div>

                  <!-- Feature 2 -->
                  <div class="bg-white p-8 rounded-xl shadow-lg border border-slate-200 hover:shadow-xl transition-shadow">
                      <div class="bg-green-100 w-14 h-14 rounded-xl flex items-center justify-center mb-6">
                          <i class="fas fa-envelope-open-text text-green-600 text-2xl"></i>
                      </div>
                      <h3 class="text-xl font-bold text-slate-800 mb-3">Contact Extraction</h3>
                      <p class="text-slate-600 leading-relaxed">
                          Automatically extract verified emails, phone numbers, and physical addresses from company websites.
                      </p>
                  </div>

                  <!-- Feature 3 -->
                  <div class="bg-white p-8 rounded-xl shadow-lg border border-slate-200 hover:shadow-xl transition-shadow">
                      <div class="bg-purple-100 w-14 h-14 rounded-xl flex items-center justify-center mb-6">
                          <i class="fas fa-users text-purple-600 text-2xl"></i>
                      </div>
                      <h3 class="text-xl font-bold text-slate-800 mb-3">Key Personnel</h3>
                      <p class="text-slate-600 leading-relaxed">
                          Identify decision-makers including CEOs, Founders, and Directors with LinkedIn profiles.
                      </p>
                  </div>
              </div>
          </section>
      `;
  }
};

// Global Functions
function showNewResearchModal() {
  alert('New Research Modal - Coming Soon!');
}

function scrollToFeatures() {
  const featuresSection = document.getElementById('features');
  if (featuresSection) {
      featuresSection.scrollIntoView({ behavior: 'smooth' });
  }
}

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
  console.log('Research Automation App Initialized');
  
  // Render Navbar
  const navbarContainer = document.getElementById('navbar');
  if (navbarContainer) {
      navbarContainer.innerHTML = Navbar.render();
  }
  
  // Render Home Content
  const appContainer = document.getElementById('app');
  if (appContainer) {
      appContainer.innerHTML = Home.render();
  }
});