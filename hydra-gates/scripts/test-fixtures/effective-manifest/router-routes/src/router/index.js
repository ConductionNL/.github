// Hand-written vue-router table — this fixture's app renders no manifest pages.
import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'

export default createRouter({
	history: createWebHistory(),
	routes: [
		{ path: '/', name: 'Dashboard', component: Dashboard },
		{ path: '/projects', name: 'ProjectList', component: Dashboard },
		{ path: '/projects/:id', name: 'ProjectBoard', component: Dashboard },
		{ path: '/:pathMatch(.*)*', redirect: '/' },
	],
})
