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
                          <a href="#how-it-works" class="text-slate-600 hover:text-primary transition-colors">
                              <i class="fas fa-cog mr-2"></i>How It Works
                          </a>
                      </div>

                      <!-- Action Buttons -->
                      <div class="flex items-center space-x-3">
                          <button onclick="App.showNewResearchModal()" 
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

export default Navbar;