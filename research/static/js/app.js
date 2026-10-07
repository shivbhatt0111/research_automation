// =========================================
// API Functions (Fixed Endpoints)
// =========================================
const API = {
  baseURL: '/api',

  async getResearchList() {
      const res = await fetch(`${this.baseURL}/research/list/`);
      if (!res.ok) throw new Error('Failed to fetch research list');
      return res.json();
  },

  async getResearchStatus(id) {
      const res = await fetch(`${this.baseURL}/research/${id}/status/`);
      if (!res.ok) throw new Error('Failed to fetch research status');
      return res.json();
  },

  async createResearch(data) {
      const res = await fetch(`${this.baseURL}/research/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
      });
      if (!res.ok) {
          const err = await res.json();
          throw new Error(err.error || 'Failed to create research');
      }
      return res.json();
  },

  async deleteResearch(id) {
      const res = await fetch(`${this.baseURL}/research/${id}/delete/`, {
          method: 'DELETE'
      });
      if (!res.ok) throw new Error('Failed to delete research');
  }
};
// =========================================
// Navbar Component
// =========================================

const Navbar = {
  render() {
      return `
          <nav class="bg-white shadow-sm border-b border-slate-200 sticky top-0 z-50">
              <div class="container mx-auto px-4">
                  <div class="flex justify-between items-center h-16">
                      <div class="flex items-center space-x-2 cursor-pointer" onclick="App.showHomePage()">
                          <div class="bg-primary p-2 rounded-lg">
                              <i class="fas fa-search text-white text-xl"></i>
                          </div>
                          <div>
                              <h1 class="text-xl font-bold text-slate-800">Research Automation</h1>
                              <p class="text-xs text-slate-500">Intelligent Company Discovery</p>
                          </div>
                      </div>
                      <div class="hidden md:flex items-center space-x-8">
                          <button onclick="App.showDashboard()" class="text-slate-600 hover:text-primary transition-colors font-medium">
                              <i class="fas fa-home mr-2"></i>Dashboard
                          </button>
                          <button onclick="App.showDataView()" class="text-slate-600 hover:text-primary transition-colors font-medium">
                              <i class="fas fa-database mr-2"></i>Database
                          </button>
                      </div>
                      <button onclick="App.showNewResearchModal()" 
                              class="bg-primary hover:bg-indigo-700 text-white px-5 py-2.5 rounded-lg font-medium transition-all shadow-lg shadow-indigo-500/30 flex items-center space-x-2">
                          <i class="fas fa-plus-circle"></i>
                          <span>New Research</span>
                      </button>
                  </div>
              </div>
          </nav>
      `;
  }
};



// =========================================
// HomePage Component (Landing Page)
// =========================================
const HomePage = {
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
                          <button onclick="App.showDashboard()" 
                                  class="bg-white text-indigo-700 px-8 py-4 rounded-xl font-bold text-lg hover:bg-indigo-50 transition-all shadow-xl">
                              <i class="fas fa-rocket mr-2"></i>Go to Dashboard
                          </button>
                          <button onclick="App.showNewResearchModal()" 
                                  class="bg-indigo-800/50 backdrop-blur-sm text-white px-8 py-4 rounded-xl font-bold text-lg hover:bg-indigo-800/70 transition-all border border-indigo-400">
                              <i class="fas fa-plus-circle mr-2"></i>New Research
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
                  <div class="bg-white p-8 rounded-xl shadow-lg border border-slate-200 hover:shadow-xl transition-shadow">
                      <div class="bg-indigo-100 w-14 h-14 rounded-xl flex items-center justify-center mb-6">
                          <i class="fas fa-search text-primary text-2xl"></i>
                      </div>
                      <h3 class="text-xl font-bold text-slate-800 mb-3">Smart Discovery</h3>
                      <p class="text-slate-600 leading-relaxed">
                          AI-powered search to find companies by industry, location, and specific criteria with verified websites.
                      </p>
                  </div>

                  <div class="bg-white p-8 rounded-xl shadow-lg border border-slate-200 hover:shadow-xl transition-shadow">
                      <div class="bg-green-100 w-14 h-14 rounded-xl flex items-center justify-center mb-6">
                          <i class="fas fa-envelope-open-text text-green-600 text-2xl"></i>
                      </div>
                      <h3 class="text-xl font-bold text-slate-800 mb-3">Contact Extraction</h3>
                      <p class="text-slate-600 leading-relaxed">
                          Automatically extract verified emails, phone numbers, and physical addresses from company websites.
                      </p>
                  </div>

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

          <!-- CTA Section -->
          <section class="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl p-12 text-center text-white shadow-2xl mb-8">
              <h2 class="text-3xl md:text-4xl font-bold mb-4">Ready to Start Your Research?</h2>
              <p class="text-xl text-indigo-100 mb-8 max-w-2xl mx-auto">
                  Save hours of manual work. Get verified company data in minutes.
              </p>
              <div class="flex flex-col sm:flex-row justify-center space-y-4 sm:space-y-0 sm:space-x-4">
                  <button onclick="App.showDashboard()" 
                          class="bg-white text-indigo-700 px-10 py-4 rounded-xl font-bold text-lg hover:bg-indigo-50 transition-all shadow-xl">
                      <i class="fas fa-chart-line mr-2"></i>View Dashboard
                  </button>
                  <button onclick="App.showNewResearchModal()" 
                          class="bg-indigo-800/50 backdrop-blur-sm text-white px-10 py-4 rounded-xl font-bold text-lg hover:bg-indigo-800/70 transition-all border border-indigo-400">
                      <i class="fas fa-plus-circle mr-2"></i>Create New Research
                  </button>
              </div>
          </section>
      `;
  }
};






// =========================================
// Dashboard Component
// =========================================
const Dashboard = {
  async render() {
      try {
          const response = await API.getResearchList();
          const list = Array.isArray(response) ? response : (response.results || []);
          
          if (list.length === 0) {
              return `
                  <div class="text-center py-20">
                      <div class="bg-indigo-100 w-24 h-24 rounded-full flex items-center justify-center mx-auto mb-6">
                          <i class="fas fa-search text-primary text-4xl"></i>
                      </div>
                      <h2 class="text-2xl font-bold text-slate-800 mb-3">No Research Tasks Yet</h2>
                      <p class="text-slate-600 mb-8">Start your first company research task to discover verified businesses.</p>
                      <button onclick="App.showNewResearchModal()" 
                              class="bg-primary hover:bg-indigo-700 text-white px-8 py-3 rounded-lg font-medium transition-all">
                          <i class="fas fa-plus-circle mr-2"></i>Create First Research
                      </button>
                  </div>
              `;
          }

          let cardsHTML = list.map(r => {
              const statusColors = {
                  'PENDING': 'bg-yellow-100 text-yellow-800',
                  'RUNNING': 'bg-blue-100 text-blue-800',
                  'COMPLETED': 'bg-green-100 text-green-800',
                  'FAILED': 'bg-red-100 text-red-800'
              };
              const statusColor = statusColors[r.status] || 'bg-gray-100 text-gray-800';
              const statusIcon = {
                  'PENDING': 'fa-clock',
                  'RUNNING': 'fa-spinner fa-spin',
                  'COMPLETED': 'fa-check-circle',
                  'FAILED': 'fa-times-circle'
              };

              return `
                  <div class="bg-white rounded-xl shadow-lg border border-slate-200 p-6 hover:shadow-xl transition-shadow relative group">
                      <!-- Delete Button -->
                      <button onclick="App.confirmDelete(${r.id}, event)" 
                              class="absolute top-4 right-4 text-slate-400 hover:text-red-600 transition-colors opacity-0 group-hover:opacity-100"
                              title="Delete this research task">
                          <i class="fas fa-trash-alt text-lg"></i>
                      </button>

                      <div class="flex justify-between items-start mb-4 pr-8">
                          <div class="flex-1 cursor-pointer" onclick="App.showResearchDetail(${r.id})">
                              <h3 class="text-lg font-bold text-slate-800 mb-1">${r.industry || 'N/A'}</h3>
                              <p class="text-sm text-slate-500"><i class="fas fa-map-marker-alt mr-1"></i>${r.location || 'N/A'}</p>
                          </div>
                          <span class="px-3 py-1 rounded-full text-xs font-medium ${statusColor}">
                              <i class="fas ${statusIcon[r.status]} mr-1"></i>${r.status}
                          </span>
                      </div>
                      <div class="grid grid-cols-3 gap-4 pt-4 border-t border-slate-100">
                          <div>
                              <p class="text-xs text-slate-500">Target</p>
                              <p class="font-bold text-slate-800">${r.top_companies || 0}</p>
                          </div>
                          <div>
                              <p class="text-xs text-slate-500">Found</p>
                              <p class="font-bold text-slate-800">${r.total_companies || 0}</p>
                          </div>
                          <div>
                              <p class="text-xs text-slate-500">Emails</p>
                              <p class="font-bold text-green-600">${r.emails_found || 0}</p>
                          </div>
                      </div>
                      <div class="mt-4 text-xs text-slate-400">
                          <i class="fas fa-clock mr-1"></i>${r.created_at || 'N/A'}
                      </div>
                  </div>
              `;
          }).join('');

          return `
              <div class="mb-8">
                  <h2 class="text-3xl font-bold text-slate-800 mb-2">Dashboard</h2>
                  <p class="text-slate-600">Manage and monitor your research tasks</p>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  ${cardsHTML}
              </div>
          `;
      } catch (error) {
          console.error('Dashboard error:', error);
          return `<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">Error loading dashboard. Please refresh the page.</div>`;
      }
  }
};



// =========================================
// Data View Component (Filtered Database)
// =========================================
const DataView = {
  filters: { industry: '', location: '', search: '' },
  data: [],
  isLoading: false,

  async fetch_data() {
      this.isLoading = true;
      const appContainer = document.getElementById('app');
      if (appContainer) {
          appContainer.innerHTML = '<div class="flex justify-center items-center h-64"><div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div></div>';
      }

      try {
          const params = new URLSearchParams();
          if (this.filters.industry) params.append('industry', this.filters.industry);
          if (this.filters.location) params.append('location', this.filters.location);
          if (this.filters.search) params.append('search', this.filters.search);
          params.append('page_size', '50'); // Load up to 50 records

          const res = await fetch(`/api/data/?${params.toString()}`);
          if (!res.ok) throw new Error('Failed to fetch data');
          const result = await res.json();
          this.data = result.results || [];
          this.render();
      } catch (error) {
          console.error('Data fetch error:', error);
          const appContainer = document.getElementById('app');
          if (appContainer) {
              appContainer.innerHTML = `<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">Error loading data: ${error.message}</div>`;
          }
      } finally {
          this.isLoading = false;
      }
  },

  handleFilterChange(e) {
      this.filters[e.target.name] = e.target.value;
  },

  handleSearch(e) {
      e.preventDefault();
      this.fetch_data();
  },

  render() {
      const appContainer = document.getElementById('app');
      if (!appContainer) return;

      const rows = this.data.map(item => `
          <tr class="border-b border-slate-100 hover:bg-slate-50 transition-colors">
              <td class="py-4 px-4">
                  <div class="font-medium text-slate-800">${item.company_name || 'N/A'}</div>
                  <a href="${item.website || '#'}" target="_blank" class="text-xs text-primary hover:underline">${item.website || 'No website'}</a>
              </td>
              <td class="py-4 px-4 text-sm text-slate-600">${item.task_industry || 'N/A'}</td>
              <td class="py-4 px-4 text-sm text-slate-600">${item.task_location || 'N/A'}</td>
              <td class="py-4 px-4 text-sm">
                  ${item.email ? `<span class="text-green-600"><i class="fas fa-envelope mr-1"></i>${item.email}</span>` : '<span class="text-slate-400">N/A</span>'}
              </td>
              <td class="py-4 px-4 text-sm">
                  ${item.phone ? `<span class="text-blue-600"><i class="fas fa-phone mr-1"></i>${item.phone}</span>` : '<span class="text-slate-400">N/A</span>'}
              </td>
              <td class="py-4 px-4 text-sm">
                  ${item.is_verified ? '<span class="bg-green-100 text-green-800 px-2 py-1 rounded text-xs font-medium">Verified</span>' : '<span class="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs font-medium">Unverified</span>'}
              </td>
          </tr>
      `).join('');

      appContainer.innerHTML = `
          <div class="mb-8 animate-fade-in">
              <div class="flex justify-between items-center mb-6">
                  <div>
                      <h2 class="text-3xl font-bold text-slate-800 mb-2">Company Database</h2>
                      <p class="text-slate-600">Search and filter verified company records from your research tasks.</p>
                  </div>
                  <button onclick="App.showDashboard()" class="text-primary hover:underline">
                      <i class="fas fa-arrow-left mr-2"></i>Back to Dashboard
                  </button>
              </div>

              <!-- Filters Form -->
              <form onsubmit="DataView.handleSearch(event)" class="bg-white p-6 rounded-xl shadow-lg border border-slate-200 mb-6">
                  <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                      <div>
                          <label class="block text-sm font-medium text-slate-700 mb-1">Industry</label>
                          <input type="text" name="industry" value="${this.filters.industry}" oninput="DataView.handleFilterChange(event)" placeholder="e.g., textile" class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none">
                      </div>
                      <div>
                          <label class="block text-sm font-medium text-slate-700 mb-1">Location</label>
                          <input type="text" name="location" value="${this.filters.location}" oninput="DataView.handleFilterChange(event)" placeholder="e.g., Indore" class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none">
                      </div>
                      <div>
                          <label class="block text-sm font-medium text-slate-700 mb-1">Search</label>
                          <input type="text" name="search" value="${this.filters.search}" oninput="DataView.handleFilterChange(event)" placeholder="Company name, email..." class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none">
                      </div>
                      <div class="flex items-end">
                          <button type="submit" class="w-full bg-primary hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-medium transition-all flex items-center justify-center space-x-2">
                              <i class="fas fa-search"></i>
                              <span>Filter Data</span>
                          </button>
                      </div>
                  </div>
              </form>

              <!-- Results Table -->
              <div class="bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden">
                  <div class="p-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
                      <h3 class="font-bold text-slate-800">Results (${this.data.length} found)</h3>
                  </div>
                  <div class="overflow-x-auto">
                      <table class="w-full text-left">
                          <thead class="bg-slate-50 text-slate-600 text-sm uppercase">
                              <tr>
                                  <th class="py-3 px-4 font-semibold">Company</th>
                                  <th class="py-3 px-4 font-semibold">Industry</th>
                                  <th class="py-3 px-4 font-semibold">Location</th>
                                  <th class="py-3 px-4 font-semibold">Email</th>
                                  <th class="py-3 px-4 font-semibold">Phone</th>
                                  <th class="py-3 px-4 font-semibold">Status</th>
                              </tr>
                          </thead>
                          <tbody class="text-sm">
                              ${this.data.length > 0 ? rows : '<tr><td colspan="6" class="py-8 text-center text-slate-500">No companies found matching your filters. Try running a new research task.</td></tr>'}
                          </tbody>
                      </table>
                  </div>
              </div>
          </div>
      `;
  }
};






// =========================================
// Research Detail Component
// =========================================

const ResearchDetail = {
  currentId: null,
  pollInterval: null,

  async render(id) {
      this.currentId = id;
      try {
          const data = await API.getResearchStatus(id);
          
          const statusColors = {
              'PENDING': 'bg-yellow-100 text-yellow-800',
              'RUNNING': 'bg-blue-100 text-blue-800',
              'COMPLETED': 'bg-green-100 text-green-800',
              'FAILED': 'bg-red-100 text-red-800'
          };
          const statusColor = statusColors[data.status] || 'bg-gray-100 text-gray-800';

          let contactsHTML = '';
          if (data.contacts && data.contacts.length > 0) {
              contactsHTML = data.contacts.map(c => `
                  <div class="bg-white rounded-xl shadow-lg border border-slate-200 p-6 mb-4">
                      <div class="flex justify-between items-start mb-4">
                          <div>
                              <h3 class="text-xl font-bold text-slate-800">${c.company_name || 'N/A'}</h3>
                              <a href="${c.website || '#'}" target="_blank" class="text-sm text-primary hover:underline">
                                  <i class="fas fa-globe mr-1"></i>${c.website || 'No website'}
                              </a>
                          </div>
                          ${c.is_verified ? '<span class="bg-green-100 text-green-800 px-3 py-1 rounded-full text-xs font-medium"><i class="fas fa-check-circle mr-1"></i>Verified</span>' : ''}
                      </div>
                      
                      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                          <div class="bg-slate-50 p-3 rounded-lg">
                              <p class="text-xs text-slate-500 mb-1"><i class="fas fa-envelope mr-1"></i>Email</p>
                              <p class="font-medium text-slate-800">${c.email || 'Not found'}</p>
                          </div>
                          <div class="bg-slate-50 p-3 rounded-lg">
                              <p class="text-xs text-slate-500 mb-1"><i class="fas fa-phone mr-1"></i>Phone</p>
                              <p class="font-medium text-slate-800">${c.phone || 'Not found'}</p>
                          </div>
                          <div class="bg-slate-50 p-3 rounded-lg md:col-span-2">
                              <p class="text-xs text-slate-500 mb-1"><i class="fas fa-map-marker-alt mr-1"></i>Address</p>
                              <p class="font-medium text-slate-800">${c.address || 'Not found'}</p>
                          </div>
                      </div>

                      ${c.key_persons && c.key_persons.length > 0 ? `
                          <div class="border-t border-slate-200 pt-4">
                              <p class="text-sm font-medium text-slate-700 mb-3"><i class="fas fa-users mr-2"></i>Key Personnel</p>
                              <div class="space-y-2">
                                  ${c.key_persons.map(p => `
                                      <div class="flex items-center justify-between bg-indigo-50 p-3 rounded-lg">
                                          <div>
                                              <p class="font-medium text-slate-800">${p.name || 'N/A'}</p>
                                              <p class="text-xs text-slate-500">${p.designation || 'N/A'}</p>
                                          </div>
                                          <div class="text-sm">
                                              ${p.email ? `<a href="mailto:${p.email}" class="text-primary hover:underline mr-3"><i class="fas fa-envelope"></i></a>` : ''}
                                              ${p.linkedin_url ? `<a href="${p.linkedin_url}" target="_blank" class="text-blue-600 hover:underline"><i class="fab fa-linkedin"></i></a>` : ''}
                                          </div>
                                      </div>
                                  `).join('')}
                              </div>
                          </div>
                      ` : ''}
                  </div>
              `).join('');
          } else {
              contactsHTML = '<p class="text-center text-slate-500 py-8">No contacts found yet.</p>';
          }

          // User-friendly status message instead of technical error
          let statusMessage = '';
          if (data.status === 'FAILED') {
              statusMessage = `
                  <div class="mt-4 bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded-lg">
                      <i class="fas fa-info-circle mr-2"></i>
                      <strong>Research could not be completed.</strong> Please try again with different search criteria.
                  </div>
              `;
          } else if (data.status === 'COMPLETED' && data.total_companies === 0) {
              statusMessage = `
                  <div class="mt-4 bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-lg">
                      <i class="fas fa-info-circle mr-2"></i>
                      <strong>No companies found</strong> matching your criteria. Try adjusting your search parameters.
                  </div>
              `;
          }

          return `
              <div class="mb-6">
                  <button onclick="App.showDashboard()" class="text-primary hover:underline mb-4 inline-block">
                      <i class="fas fa-arrow-left mr-2"></i>Back to Dashboard
                  </button>
                  <div class="bg-white rounded-xl shadow-lg border border-slate-200 p-6 mb-6">
                      <div class="flex justify-between items-start mb-4">
                          <div>
                              <h2 class="text-2xl font-bold text-slate-800 mb-2">${data.industry || 'N/A'}</h2>
                              <p class="text-slate-600"><i class="fas fa-map-marker-alt mr-2"></i>${data.location || 'N/A'}</p>
                          </div>
                          <span class="px-4 py-2 rounded-full text-sm font-medium ${statusColor}">
                              ${data.status}
                          </span>
                      </div>
                      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-slate-100">
                          <div>
                              <p class="text-xs text-slate-500">Target Companies</p>
                              <p class="text-xl font-bold text-slate-800">${data.top_companies || 0}</p>
                          </div>
                          <div>
                              <p class="text-xs text-slate-500">Total Found</p>
                              <p class="text-xl font-bold text-slate-800">${data.total_companies || 0}</p>
                          </div>
                          <div>
                              <p class="text-xs text-slate-500">Emails Found</p>
                              <p class="text-xl font-bold text-green-600">${data.emails_found || 0}</p>
                          </div>
                          <div>
                              <p class="text-xs text-slate-500">Phones Found</p>
                              <p class="text-xl font-bold text-blue-600">${data.phones_found || 0}</p>
                          </div>
                      </div>
                      ${statusMessage}
                      ${data.duration ? `<div class="mt-4 text-sm text-slate-500"><i class="fas fa-clock mr-1"></i>Duration: ${data.duration}</div>` : ''}
                  </div>

                  <h3 class="text-xl font-bold text-slate-800 mb-4">
                      <i class="fas fa-address-book mr-2"></i>Contacts (${data.contacts ? data.contacts.length : 0})
                  </h3>
                  ${contactsHTML}
              </div>
          `;
      } catch (error) {
          console.error('Detail error:', error);
          return `<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">Error loading research details. Please try again.</div>`;
      }
  }
};




// =========================================
// New Research Modal
// =========================================
const NewResearchModal = {
  render() {
      return `
          <div id="modal-overlay" class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onclick="App.closeModal(event)">
              <div class="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto" onclick="event.stopPropagation()">
                  <div class="p-6 border-b border-slate-200">
                      <div class="flex justify-between items-center">
                          <h2 class="text-2xl font-bold text-slate-800">
                              <i class="fas fa-plus-circle text-primary mr-2"></i>New Research Task
                          </h2>
                          <button onclick="App.closeModal()" class="text-slate-400 hover:text-slate-600 text-2xl">
                              <i class="fas fa-times"></i>
                          </button>
                      </div>
                  </div>
                  <form id="research-form" onsubmit="App.handleNewResearch(event)" class="p-6 space-y-6">
                      <div>
                          <label class="block text-sm font-medium text-slate-700 mb-2">
                              <i class="fas fa-industry mr-1"></i>Industry *
                          </label>
                          <input type="text" id="industry" required
                                 placeholder="e.g., textile manufacturing companies"
                                 class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all">
                          <p class="text-xs text-slate-500 mt-1">Describe the industry or business type you want to research</p>
                      </div>
                      
                      <div>
                          <label class="block text-sm font-medium text-slate-700 mb-2">
                              <i class="fas fa-map-marker-alt mr-1"></i>Location *
                          </label>
                          <input type="text" id="location" required
                                 placeholder="e.g., Sanwer Road Industrial Area, Indore"
                                 class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all">
                          <p class="text-xs text-slate-500 mt-1">City, area, or region where companies should be located</p>
                      </div>
                      
                      <div>
                          <label class="block text-sm font-medium text-slate-700 mb-2">
                              <i class="fas fa-building mr-1"></i>Number of Companies *
                          </label>
                          <input type="number" id="top_companies" required min="1" max="100" value="10"
                                 class="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all">
                          <p class="text-xs text-slate-500 mt-1">How many companies you want to discover (1-100)</p>
                      </div>

                      <div class="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
                          <p class="text-sm text-indigo-800">
                              <i class="fas fa-info-circle mr-2"></i>
                              <strong>What happens next?</strong> Our AI will search for companies matching your criteria, extract verified contact details, and identify key decision-makers.
                          </p>
                      </div>

                      <div class="flex justify-end space-x-3 pt-4 border-t border-slate-200">
                          <button type="button" onclick="App.closeModal()" 
                                  class="px-6 py-3 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 font-medium transition-all">
                              Cancel
                          </button>
                          <button type="submit" 
                                  class="px-6 py-3 bg-primary hover:bg-indigo-700 text-white rounded-lg font-medium transition-all shadow-lg shadow-indigo-500/30">
                              <i class="fas fa-rocket mr-2"></i>Start Research
                          </button>
                      </div>
                  </form>
              </div>
          </div>
      `;
  }
};

// =========================================
// Main App Controller
// =========================================
const App = {
  init() {
      this.renderNavbar();
      this.showHomePage(); // Changed to show HomePage first
      console.log('Research Automation App Initialized');
  },

  renderNavbar() {
      const navbarContainer = document.getElementById('navbar');
      if (navbarContainer) {
          navbarContainer.innerHTML = Navbar.render();
      }
  },

  showHomePage() {
      const appContainer = document.getElementById('app');
      if (appContainer) {
          appContainer.innerHTML = HomePage.render();
      }
      // Clear polling when returning to homepage
      if (ResearchDetail.pollInterval) {
          clearInterval(ResearchDetail.pollInterval);
          ResearchDetail.pollInterval = null;
      }
  },

  async showDashboard() {
      const appContainer = document.getElementById('app');
      if (appContainer) {
          appContainer.innerHTML = '<div class="flex justify-center items-center h-64"><div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div></div>';
          appContainer.innerHTML = await Dashboard.render();
      }
      
      // Clear any existing polling intervals when returning to dashboard
      if (ResearchDetail.pollInterval) {
          clearInterval(ResearchDetail.pollInterval);
          ResearchDetail.pollInterval = null;
      }
  },




  async showDataView() {
    const appContainer = document.getElementById('app');
    if (appContainer) {
        appContainer.innerHTML = '<div class="flex justify-center items-center h-64"><div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div></div>';
    }
    await DataView.fetch_data();
    
    // Clear polling when viewing data
    if (ResearchDetail.pollInterval) {
        clearInterval(ResearchDetail.pollInterval);
        ResearchDetail.pollInterval = null;
    }
},





  async showResearchDetail(id) {
      const appContainer = document.getElementById('app');
      if (appContainer) {
          appContainer.innerHTML = '<div class="flex justify-center items-center h-64"><div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div></div>';
          appContainer.innerHTML = await ResearchDetail.render(id);
          
          // Auto-refresh if status is RUNNING or PENDING
          try {
              const data = await API.getResearchStatus(id);
              if (data.status === 'RUNNING' || data.status === 'PENDING') {
                  ResearchDetail.pollInterval = setInterval(async () => {
                      const updated = await API.getResearchStatus(id);
                      // Re-render to show live progress
                      appContainer.innerHTML = await ResearchDetail.render(id);
                      
                      // Stop polling if completed or failed
                      if (updated.status !== 'RUNNING' && updated.status !== 'PENDING') {
                          clearInterval(ResearchDetail.pollInterval);
                          ResearchDetail.pollInterval = null;
                      }
                  }, 5000); // Poll every 5 seconds
              }
          } catch (error) {
              console.error('Polling error:', error);
          }
      }
  },

  confirmDelete(id, event) {
      if (event) {
          event.stopPropagation(); // Prevent card click from triggering
      }
      
      if (confirm('Are you sure you want to delete this research task? This action cannot be undone and will remove all associated data.')) {
          this.deleteResearch(id);
      }
  },

  async deleteResearch(id) {
      try {
          await API.deleteResearch(id);
          this.showNotification('Research task deleted successfully', 'success');
          await this.showDashboard();
      } catch (error) {
          console.error('Delete error:', error);
          this.showNotification('Failed to delete research task. Please try again.', 'error');
      }
  },

  showNewResearchModal() {
      const modalHTML = NewResearchModal.render();
      let modalContainer = document.getElementById('modal-container');
      if (!modalContainer) {
          modalContainer = document.createElement('div');
          modalContainer.id = 'modal-container';
          document.body.appendChild(modalContainer);
      }
      modalContainer.innerHTML = modalHTML;
  },

  closeModal(event) {
      if (event && event.target !== event.currentTarget) return;
      const modalContainer = document.getElementById('modal-container');
      if (modalContainer) {
          modalContainer.innerHTML = '';
      }
  },

  async handleNewResearch(event) {
      event.preventDefault();
      
      const industry = document.getElementById('industry').value.trim();
      const location = document.getElementById('location').value.trim();
      const top_companies = parseInt(document.getElementById('top_companies').value);

      if (!industry || !location || !top_companies) {
          this.showNotification('Please fill all required fields', 'error');
          return;
      }

      const submitBtn = event.target.querySelector('button[type="submit"]');
      const originalHTML = submitBtn.innerHTML;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Creating...';
      submitBtn.disabled = true;

      try {
          const data = await API.createResearch({ industry, location, top_companies });
          this.closeModal();
          
          // Show success notification
          this.showNotification('Research task created successfully!', 'success');
          
          // Auto-navigate to detail page after a short delay
          if (data.id) {
              setTimeout(() => this.showResearchDetail(data.id), 1000);
          } else {
              await this.showDashboard();
          }
      } catch (error) {
          console.error('Create error:', error);
          this.showNotification(error.message || 'Failed to create research task', 'error');
      } finally {
          submitBtn.innerHTML = originalHTML;
          submitBtn.disabled = false;
      }
  },

  showNotification(message, type = 'info') {
      const colors = {
          success: 'bg-green-500',
          error: 'bg-red-500',
          info: 'bg-blue-500'
      };
      const icons = {
          success: 'fa-check-circle',
          error: 'fa-exclamation-circle',
          info: 'fa-info-circle'
      };
      
      const notif = document.createElement('div');
      notif.className = `fixed top-20 right-4 ${colors[type]} text-white px-6 py-4 rounded-lg shadow-2xl z-50 animate-fade-in flex items-center space-x-3`;
      notif.innerHTML = `<i class="fas ${icons[type]}"></i><span>${message}</span>`;
      document.body.appendChild(notif);
      
      setTimeout(() => {
          notif.style.opacity = '0';
          notif.style.transition = 'opacity 0.5s';
          setTimeout(() => notif.remove(), 500);
      }, 3000);
  }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});