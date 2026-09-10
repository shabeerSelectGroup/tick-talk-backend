import { createRouter, createWebHistory } from 'vue-router'
import { adminAuthGuard, participantAuthGuard } from '@/router/guards'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // Participant
    {
      path: '/',
      name: 'join',
      component: () => import('@/views/participant/JoinView.vue'),
      meta: { layout: 'participant', guest: true },
    },
    {
      path: '/join/:eventCode',
      name: 'join-with-code',
      component: () => import('@/views/participant/JoinView.vue'),
      meta: { layout: 'participant', guest: true },
    },
    {
      path: '/home',
      redirect: { name: 'tasks' },
    },
    {
      path: '/tasks',
      name: 'tasks',
      component: () => import('@/views/participant/TasksView.vue'),
      meta: { layout: 'participant', requiresSession: true },
    },
    {
      path: '/tasks/:participantTaskId/flow',
      name: 'task-flow',
      component: () => import('@/views/participant/TaskFlowView.vue'),
      meta: { layout: 'participant', requiresSession: true },
    },
    {
      path: '/badge',
      redirect: { name: 'tasks' },
    },
    {
      path: '/scan',
      redirect: { name: 'tasks' },
    },
    {
      path: '/leaderboard',
      name: 'leaderboard',
      component: () => import('@/views/participant/LeaderboardView.vue'),
      meta: { layout: 'participant', requiresSession: true },
    },
    {
      path: '/profile',
      redirect: { name: 'tasks' },
    },
    // Public wall
    {
      path: '/wall/:eventCode',
      name: 'wall',
      component: () => import('@/views/wall/WallView.vue'),
      meta: { layout: 'wall' },
    },
    // Admin auth
    {
      path: '/admin/login',
      name: 'admin-login',
      component: () => import('@/views/admin/LoginView.vue'),
      meta: { layout: 'admin', guestAdmin: true },
    },
    {
      path: '/admin/logout',
      name: 'admin-logout',
      component: () => import('@/views/admin/LogoutView.vue'),
      meta: { layout: 'admin' },
    },
    {
      path: '/admin',
      redirect: '/admin/dashboard',
    },
    {
      path: '/admin/dashboard',
      name: 'admin-dashboard',
      component: () => import('@/views/admin/DashboardView.vue'),
      meta: { layout: 'admin', requiresAdmin: true },
    },
    {
      path: '/admin/events',
      name: 'admin-events',
      component: () => import('@/views/admin/EventsListView.vue'),
      meta: { layout: 'admin', requiresAdmin: true },
    },
    {
      path: '/admin/events/create',
      name: 'admin-events-create',
      component: () => import('@/views/admin/EventCreateView.vue'),
      meta: { layout: 'admin', requiresAdmin: true },
    },
    {
      path: '/admin/events/:id',
      name: 'admin-event-detail',
      component: () => import('@/views/admin/EventDetailView.vue'),
      meta: { layout: 'admin', requiresAdmin: true },
    },
    {
      path: '/admin/events/:id/tasks',
      name: 'admin-event-tasks',
      component: () => import('@/views/admin/EventTasksView.vue'),
      meta: { layout: 'admin', requiresAdmin: true },
    },
    {
      path: '/admin/events/:id/participants',
      name: 'admin-event-participants',
      component: () => import('@/views/admin/EventParticipantsView.vue'),
      meta: { layout: 'admin', requiresAdmin: true },
    },
    {
      path: '/admin/events/:id/gallery',
      name: 'admin-event-gallery',
      component: () => import('@/views/admin/EventGalleryView.vue'),
      meta: { layout: 'admin', requiresAdmin: true },
    },
    {
      path: '/admin/events/:id/reports',
      name: 'admin-event-reports',
      component: () => import('@/views/admin/EventReportsView.vue'),
      meta: { layout: 'admin', requiresAdmin: true },
    },
    {
      path: '/admin/events/:id/leaderboard',
      name: 'admin-event-leaderboard',
      component: () => import('@/views/admin/EventLeaderboardView.vue'),
      meta: { layout: 'admin', requiresAdmin: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const participantResult = await participantAuthGuard(to)
  if (participantResult !== true) return participantResult

  const adminResult = await adminAuthGuard(to)
  return adminResult
})

export default router
