import React, { useState, useEffect, useCallback } from 'react';
import { API } from '../config/api';
import { useAuth } from '../contexts/AuthContext';
import { Navbar } from '../components/Navbar';
import {
  LayoutDashboard,
  FileText,
  Flag,
  Tag,
  ClipboardList,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Search,
  Filter,
  Eye,
  EyeOff,
  Lock,
  Trash2,
  Pin,
  PinOff,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Shield,
  BarChart3,
  MessageCircle,
  Users,
  Clock,
  BookOpen,
  Edit3,
  X,
  Save,
  Plus
} from 'lucide-react';

const TABS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'posts', label: 'Publicaciones', icon: FileText },
  { id: 'reports', label: 'Reportes', icon: Flag },
  { id: 'categories', label: 'Categorías', icon: Tag },
  { id: 'audit', label: 'Auditoría', icon: ClipboardList }
];

const STATUS_MAP = {
  active: { label: 'Activo', color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  hidden: { label: 'Oculto', color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
  closed: { label: 'Cerrado', color: 'text-blue-400', bg: 'bg-blue-500/10' },
  deleted: { label: 'Eliminado', color: 'text-[#D92B2B]', bg: 'bg-[#D92B2B]/10' },
  pending: { label: 'Pendiente', color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
  resolved: { label: 'Resuelto', color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  dismissed: { label: 'Descartado', color: 'text-[#606060]', bg: 'bg-white/5' }
};

export default function AdminForumPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');

  const [stats, setStats] = useState(null);
  const [posts, setPosts] = useState([]);
  const [postsMeta, setPostsMeta] = useState({ total: 0, page: 1, pages: 1 });
  const [postsStatusFilter, setPostsStatusFilter] = useState('');
  const [postsPage, setPostsPage] = useState(1);
  const [postsLoading, setPostsLoading] = useState(false);

  const [reports, setReports] = useState([]);
  const [reportsMeta, setReportsMeta] = useState({ total: 0, page: 1, pages: 1 });
  const [reportsStatusFilter, setReportsStatusFilter] = useState('');
  const [reportsPage, setReportsPage] = useState(1);
  const [reportsLoading, setReportsLoading] = useState(false);

  const [categories, setCategories] = useState([]);
  const [categoriesLoading, setCategoriesLoading] = useState(false);
  const [categoryModal, setCategoryModal] = useState({ open: false, edit: null });
  const [categoryName, setCategoryName] = useState('');
  const [categoryDesc, setCategoryDesc] = useState('');
  const [categorySaving, setCategorySaving] = useState(false);

  const [auditLogs, setAuditLogs] = useState([]);
  const [auditLoading, setAuditLoading] = useState(false);

  const [resolveModal, setResolveModal] = useState({ open: false, report: null });
  const [resolveStatus, setResolveStatus] = useState('resolved');
  const [adminNote, setAdminNote] = useState('');
  const [resolving, setResolving] = useState(false);

  const [globalLoading, setGlobalLoading] = useState(true);

  const isAdmin = user && user.role === 'admin';

  const fetchDashboard = useCallback(async () => {
    try {
      const res = await API.get('/api/admin/forum/stats');
      setStats(res.data);
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  }, []);

  const fetchPosts = useCallback(async () => {
    setPostsLoading(true);
    try {
      const params = { page: postsPage, limit: 15 };
      if (postsStatusFilter) params.status = postsStatusFilter;
      const res = await API.get('/api/admin/forum/posts', { params });
      setPosts(res.data.posts || []);
      setPostsMeta({
        total: res.data.total || 0,
        page: res.data.page || 1,
        pages: res.data.pages || 1
      });
    } catch (err) {
      console.error('Error fetching posts:', err);
    } finally {
      setPostsLoading(false);
    }
  }, [postsPage, postsStatusFilter]);

  const fetchReports = useCallback(async () => {
    setReportsLoading(true);
    try {
      const params = { page: reportsPage, limit: 15 };
      if (reportsStatusFilter) params.status = reportsStatusFilter;
      const res = await API.get('/api/admin/forum/reports', { params });
      setReports(res.data.reports || []);
      setReportsMeta({
        total: res.data.total || 0,
        page: res.data.page || 1,
        pages: res.data.pages || 1
      });
    } catch (err) {
      console.error('Error fetching reports:', err);
    } finally {
      setReportsLoading(false);
    }
  }, [reportsPage, reportsStatusFilter]);

  const fetchCategories = useCallback(async () => {
    setCategoriesLoading(true);
    try {
      const res = await API.get('/api/forum/categories');
      setCategories(res.data.categories || res.data);
    } catch (err) {
      console.error('Error fetching categories:', err);
    } finally {
      setCategoriesLoading(false);
    }
  }, []);

  const fetchAudit = useCallback(async () => {
    setAuditLoading(true);
    try {
      const res = await API.get('/api/admin/forum/audit');
      setAuditLogs(res.data.logs || res.data);
    } catch (err) {
      console.error('Error fetching audit logs:', err);
    } finally {
      setAuditLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isAdmin) return;
    const init = async () => {
      setGlobalLoading(true);
      await fetchDashboard();
      setGlobalLoading(false);
    };
    init();
  }, [isAdmin, fetchDashboard]);

  useEffect(() => {
    if (!isAdmin) return;
    if (activeTab === 'posts') fetchPosts();
    if (activeTab === 'reports') fetchReports();
    if (activeTab === 'categories') fetchCategories();
    if (activeTab === 'audit') fetchAudit();
  }, [activeTab, isAdmin, fetchPosts, fetchReports, fetchCategories, fetchAudit]);

  useEffect(() => {
    setPostsPage(1);
  }, [postsStatusFilter]);

  useEffect(() => {
    setReportsPage(1);
  }, [reportsStatusFilter]);

  const handleStatusChange = async (postId, status) => {
    try {
      await API.put(`/api/admin/forum/posts/${postId}/status`, { status });
      fetchPosts();
    } catch (err) {
      console.error('Error changing status:', err);
    }
  };

  const handlePinToggle = async (postId) => {
    try {
      await API.put(`/api/admin/forum/posts/${postId}/pin`);
      fetchPosts();
    } catch (err) {
      console.error('Error toggling pin:', err);
    }
  };

  const handleResolveReport = async () => {
    if (!resolveModal.report) return;
    setResolving(true);
    try {
      await API.put(`/api/admin/forum/reports/${resolveModal.report.id}`, {
        status: resolveStatus,
        admin_note: adminNote
      });
      setResolveModal({ open: false, report: null });
      setAdminNote('');
      setResolveStatus('resolved');
      fetchReports();
    } catch (err) {
      console.error('Error resolving report:', err);
    } finally {
      setResolving(false);
    }
  };

  const handleCategorySave = async () => {
    if (!categoryName.trim()) return;
    setCategorySaving(true);
    try {
      if (categoryModal.edit) {
        await API.put(`/api/admin/forum/categories/${categoryModal.edit.id}`, {
          name: categoryName.trim(),
          description: categoryDesc.trim()
        });
      } else {
        await API.post('/api/admin/forum/categories', {
          name: categoryName.trim(),
          description: categoryDesc.trim()
        });
      }
      setCategoryModal({ open: false, edit: null });
      setCategoryName('');
      setCategoryDesc('');
      fetchCategories();
    } catch (err) {
      console.error('Error saving category:', err);
    } finally {
      setCategorySaving(false);
    }
  };

  const handleCategoryDeactivate = async (catId) => {
    try {
      await API.put(`/api/admin/forum/categories/${catId}/deactivate`);
      fetchCategories();
    } catch (err) {
      console.error('Error deactivating category:', err);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return d.toLocaleDateString('es-ES', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex flex-col">
        <Navbar />
        <div className="flex-1 flex flex-col items-center justify-center text-[#A0A0A0]">
          <Shield className="w-12 h-12 mb-4 text-[#D92B2B]" />
          <p className="text-lg">Acceso denegado</p>
          <p className="text-sm text-[#606060] mt-2">Se requieren permisos de administrador</p>
        </div>
      </div>
    );
  }

  if (globalLoading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex flex-col">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-[#D92B2B] animate-spin" />
        </div>
      </div>
    );
  }

  const StatCard = ({ icon: Icon, label, value, color = 'text-[#F5F5F5]' }) => (
    <div className="bg-[#121212] border border-white/10 rounded-xl p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 bg-[#D92B2B]/10 rounded-lg flex items-center justify-center">
          <Icon className="w-5 h-5 text-[#D92B2B]" />
        </div>
        <span className="text-sm text-[#A0A0A0]">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${color}`}>{value ?? '-'}</p>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center gap-3 mb-8">
          <Shield className="w-6 h-6 text-[#D92B2B]" />
          <h1 className="text-2xl font-bold text-[#F5F5F5]">Administración del Foro</h1>
        </div>

        <div className="flex items-center gap-1 bg-[#121212] border border-white/10 rounded-xl p-1 mb-8 overflow-x-auto">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-[#D92B2B] text-white'
                  : 'text-[#A0A0A0] hover:text-[#F5F5F5] hover:bg-white/5'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'dashboard' && (
          <div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <StatCard icon={FileText} label="Publicaciones" value={stats?.total_posts} />
              <StatCard icon={MessageCircle} label="Respuestas" value={stats?.total_replies} />
              <StatCard icon={Flag} label="Reportes pendientes" value={stats?.pending_reports} color="text-yellow-400" />
              <StatCard icon={Users} label="Usuarios activos" value={stats?.active_users} />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard icon={BookOpen} label="Categorías" value={stats?.total_categories} />
              <StatCard icon={BarChart3} label="Publicaciones hoy" value={stats?.posts_today} />
              <StatCard icon={Clock} label="Respuestas hoy" value={stats?.replies_today} />
              <StatCard icon={AlertTriangle} label="Reportes resueltos" value={stats?.resolved_reports} />
            </div>
          </div>
        )}

        {activeTab === 'posts' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-[#606060]" />
                <select
                  value={postsStatusFilter}
                  onChange={(e) => setPostsStatusFilter(e.target.value)}
                  className="bg-[#121212] border border-white/10 rounded-lg px-3 py-2 text-sm text-[#F5F5F5] focus:outline-none focus:border-[#D92B2B] appearance-none cursor-pointer"
                >
                  <option value="">Todos los estados</option>
                  <option value="active">Activo</option>
                  <option value="hidden">Oculto</option>
                  <option value="closed">Cerrado</option>
                  <option value="deleted">Eliminado</option>
                </select>
              </div>
              <p className="text-sm text-[#606060]">{postsMeta.total} resultados</p>
            </div>

            {postsLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-[#D92B2B] animate-spin" />
              </div>
            ) : posts.length === 0 ? (
              <div className="bg-[#121212] border border-white/10 rounded-xl p-12 text-center">
                <FileText className="w-12 h-12 text-[#606060] mx-auto mb-4" />
                <p className="text-[#A0A0A0]">No se encontraron publicaciones</p>
              </div>
            ) : (
              <>
                <div className="space-y-3">
                  {posts.map(post => (
                    <div key={post.id} className="bg-[#121212] border border-white/10 rounded-xl p-5">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2 flex-wrap">
                            <span className={`px-2 py-0.5 text-xs rounded-full ${STATUS_MAP[post.status]?.bg} ${STATUS_MAP[post.status]?.color}`}>
                              {STATUS_MAP[post.status]?.label}
                            </span>
                            {post.pinned && (
                              <span className="px-2 py-0.5 bg-[#D4AF37]/10 text-[#D4AF37] text-xs rounded-full">
                                Fijado
                              </span>
                            )}
                          </div>
                          <h3 className="text-[#F5F5F5] font-medium mb-1 truncate">{post.title}</h3>
                          <p className="text-[#606060] text-xs mb-2">
                            por {post.username} · {formatDate(post.created_at)} · {post.category_name || 'Sin categoría'}
                          </p>
                          <p className="text-[#A0A0A0] text-sm line-clamp-1">{post.content}</p>
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          <button
                            onClick={() => handlePinToggle(post.id)}
                            className={`p-2 rounded-lg transition-colors ${
                              post.pinned
                                ? 'text-[#D4AF37] bg-[#D4AF37]/10'
                                : 'text-[#606060] hover:text-[#D4AF37] hover:bg-[#D4AF37]/10'
                            }`}
                            title={post.pinned ? 'Desfijar' : 'Fijar'}
                          >
                            {post.pinned ? <PinOff className="w-4 h-4" /> : <Pin className="w-4 h-4" />}
                          </button>
                          {post.status !== 'active' && (
                            <button
                              onClick={() => handleStatusChange(post.id, 'active')}
                              className="p-2 text-[#606060] hover:text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors"
                              title="Activar"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                          )}
                          {post.status !== 'hidden' && (
                            <button
                              onClick={() => handleStatusChange(post.id, 'hidden')}
                              className="p-2 text-[#606060] hover:text-yellow-400 hover:bg-yellow-500/10 rounded-lg transition-colors"
                              title="Ocultar"
                            >
                              <EyeOff className="w-4 h-4" />
                            </button>
                          )}
                          {post.status !== 'closed' && (
                            <button
                              onClick={() => handleStatusChange(post.id, 'closed')}
                              className="p-2 text-[#606060] hover:text-blue-400 hover:bg-blue-500/10 rounded-lg transition-colors"
                              title="Cerrar"
                            >
                              <Lock className="w-4 h-4" />
                            </button>
                          )}
                          {post.status !== 'deleted' && (
                            <button
                              onClick={() => handleStatusChange(post.id, 'deleted')}
                              className="p-2 text-[#606060] hover:text-[#D92B2B] hover:bg-[#D92B2B]/10 rounded-lg transition-colors"
                              title="Eliminar"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {postsMeta.pages > 1 && (
                  <div className="flex items-center justify-center gap-2 mt-6">
                    <button
                      onClick={() => setPostsPage(p => Math.max(1, p - 1))}
                      disabled={postsPage <= 1}
                      className="p-2 text-[#606060] hover:text-[#F5F5F5] hover:bg-white/5 rounded-lg transition-colors disabled:opacity-30"
                    >
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    {Array.from({ length: Math.min(5, postsMeta.pages) }, (_, i) => {
                      const start = Math.max(1, Math.min(postsPage - 2, postsMeta.pages - 4));
                      return start + i;
                    }).filter(p => p <= postsMeta.pages).map(p => (
                      <button
                        key={p}
                        onClick={() => setPostsPage(p)}
                        className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                          p === postsPage
                            ? 'bg-[#D92B2B] text-white'
                            : 'text-[#606060] hover:text-[#F5F5F5] hover:bg-white/5'
                        }`}
                      >
                        {p}
                      </button>
                    ))}
                    <button
                      onClick={() => setPostsPage(p => Math.min(postsMeta.pages, p + 1))}
                      disabled={postsPage >= postsMeta.pages}
                      className="p-2 text-[#606060] hover:text-[#F5F5F5] hover:bg-white/5 rounded-lg transition-colors disabled:opacity-30"
                    >
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === 'reports' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-[#606060]" />
                <select
                  value={reportsStatusFilter}
                  onChange={(e) => setReportsStatusFilter(e.target.value)}
                  className="bg-[#121212] border border-white/10 rounded-lg px-3 py-2 text-sm text-[#F5F5F5] focus:outline-none focus:border-[#D92B2B] appearance-none cursor-pointer"
                >
                  <option value="">Todos los estados</option>
                  <option value="pending">Pendiente</option>
                  <option value="resolved">Resuelto</option>
                  <option value="dismissed">Descartado</option>
                </select>
              </div>
              <p className="text-sm text-[#606060]">{reportsMeta.total} resultados</p>
            </div>

            {reportsLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-[#D92B2B] animate-spin" />
              </div>
            ) : reports.length === 0 ? (
              <div className="bg-[#121212] border border-white/10 rounded-xl p-12 text-center">
                <Flag className="w-12 h-12 text-[#606060] mx-auto mb-4" />
                <p className="text-[#A0A0A0]">No se encontraron reportes</p>
              </div>
            ) : (
              <>
                <div className="space-y-3">
                  {reports.map(report => (
                    <div key={report.id} className="bg-[#121212] border border-white/10 rounded-xl p-5">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2">
                            <span className={`px-2 py-0.5 text-xs rounded-full ${STATUS_MAP[report.status]?.bg} ${STATUS_MAP[report.status]?.color}`}>
                              {STATUS_MAP[report.status]?.label}
                            </span>
                            <span className="px-2 py-0.5 bg-white/5 text-[#A0A0A0] text-xs rounded-full">
                              {report.reason}
                            </span>
                          </div>
                          <p className="text-[#F5F5F5] text-sm mb-1">
                            Reportado por: <span className="text-[#D4AF37]">{report.reporter_username}</span>
                          </p>
                          <p className="text-[#606060] text-xs mb-2">
                            {formatDate(report.created_at)}
                            {report.target_type && ` · Tipo: ${report.target_type}`}
                          </p>
                          {report.explanation && (
                            <p className="text-[#A0A0A0] text-sm mb-2 italic">"{report.explanation}"</p>
                          )}
                          {report.admin_note && (
                            <p className="text-[#606060] text-xs mt-2">
                              <Shield className="w-3 h-3 inline mr-1" />
                              Nota admin: {report.admin_note}
                            </p>
                          )}
                        </div>
                        {report.status === 'pending' && (
                          <button
                            onClick={() => {
                              setResolveModal({ open: true, report });
                              setResolveStatus('resolved');
                              setAdminNote('');
                            }}
                            className="px-3 py-1.5 bg-[#D92B2B] text-white text-xs font-medium rounded-lg hover:bg-[#F03C3C] transition-colors flex-shrink-0"
                          >
                            Revisar
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {reportsMeta.pages > 1 && (
                  <div className="flex items-center justify-center gap-2 mt-6">
                    <button
                      onClick={() => setReportsPage(p => Math.max(1, p - 1))}
                      disabled={reportsPage <= 1}
                      className="p-2 text-[#606060] hover:text-[#F5F5F5] hover:bg-white/5 rounded-lg transition-colors disabled:opacity-30"
                    >
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    {Array.from({ length: Math.min(5, reportsMeta.pages) }, (_, i) => {
                      const start = Math.max(1, Math.min(reportsPage - 2, reportsMeta.pages - 4));
                      return start + i;
                    }).filter(p => p <= reportsMeta.pages).map(p => (
                      <button
                        key={p}
                        onClick={() => setReportsPage(p)}
                        className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                          p === reportsPage
                            ? 'bg-[#D92B2B] text-white'
                            : 'text-[#606060] hover:text-[#F5F5F5] hover:bg-white/5'
                        }`}
                      >
                        {p}
                      </button>
                    ))}
                    <button
                      onClick={() => setReportsPage(p => Math.min(reportsMeta.pages, p + 1))}
                      disabled={reportsPage >= reportsMeta.pages}
                      className="p-2 text-[#606060] hover:text-[#F5F5F5] hover:bg-white/5 rounded-lg transition-colors disabled:opacity-30"
                    >
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === 'categories' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-[#F5F5F5]">Gestionar Categorías</h2>
              <button
                onClick={() => {
                  setCategoryModal({ open: true, edit: null });
                  setCategoryName('');
                  setCategoryDesc('');
                }}
                className="flex items-center gap-2 px-4 py-2 bg-[#D92B2B] text-white text-sm font-medium rounded-lg hover:bg-[#F03C3C] transition-colors"
              >
                <Plus className="w-4 h-4" />
                Nueva categoría
              </button>
            </div>

            {categoriesLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-[#D92B2B] animate-spin" />
              </div>
            ) : (
              <div className="space-y-3">
                {categories.map(cat => (
                  <div key={cat.id} className="bg-[#121212] border border-white/10 rounded-xl p-5 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-4 flex-1 min-w-0">
                      <div className="w-10 h-10 bg-[#D92B2B]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Tag className="w-5 h-5 text-[#D92B2B]" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-[#F5F5F5] font-medium">{cat.name}</h3>
                        {cat.description && (
                          <p className="text-[#606060] text-xs truncate">{cat.description}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        onClick={() => {
                          setCategoryModal({ open: true, edit: cat });
                          setCategoryName(cat.name);
                          setCategoryDesc(cat.description || '');
                        }}
                        className="p-2 text-[#606060] hover:text-[#D4AF37] hover:bg-[#D4AF37]/10 rounded-lg transition-colors"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleCategoryDeactivate(cat.id)}
                        className="p-2 text-[#606060] hover:text-[#D92B2B] hover:bg-[#D92B2B]/10 rounded-lg transition-colors"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'audit' && (
          <div>
            <h2 className="text-lg font-semibold text-[#F5F5F5] mb-6">Registro de Auditoría</h2>

            {auditLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-[#D92B2B] animate-spin" />
              </div>
            ) : auditLogs.length === 0 ? (
              <div className="bg-[#121212] border border-white/10 rounded-xl p-12 text-center">
                <ClipboardList className="w-12 h-12 text-[#606060] mx-auto mb-4" />
                <p className="text-[#A0A0A0]">No hay registros de auditoría</p>
              </div>
            ) : (
              <div className="bg-[#121212] border border-white/10 rounded-xl overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="text-left px-5 py-3 text-[#A0A0A0] font-medium">Fecha</th>
                        <th className="text-left px-5 py-3 text-[#A0A0A0] font-medium">Usuario</th>
                        <th className="text-left px-5 py-3 text-[#A0A0A0] font-medium">Acción</th>
                        <th className="text-left px-5 py-3 text-[#A0A0A0] font-medium">Detalles</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs.map((log, idx) => (
                        <tr key={log.id || idx} className="border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors">
                          <td className="px-5 py-3 text-[#606060] whitespace-nowrap">
                            {formatDate(log.created_at || log.timestamp)}
                          </td>
                          <td className="px-5 py-3 text-[#D4AF37] whitespace-nowrap">
                            {log.username || log.admin_username || '-'}
                          </td>
                          <td className="px-5 py-3 text-[#F5F5F5] whitespace-nowrap">
                            {log.action || '-'}
                          </td>
                          <td className="px-5 py-3 text-[#A0A0A0] max-w-xs truncate">
                            {log.details || log.description || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {resolveModal.open && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
            <div className="bg-[#121212] border border-white/10 rounded-xl p-6 w-full max-w-md">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-[#F5F5F5]">Resolver reporte</h3>
                <button
                  onClick={() => { setResolveModal({ open: false, report: null }); setAdminNote(''); }}
                  className="p-1 text-[#606060] hover:text-[#F5F5F5] transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4 mb-6">
                <div className="flex gap-2">
                  <button
                    onClick={() => setResolveStatus('resolved')}
                    className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border text-sm font-medium transition-colors ${
                      resolveStatus === 'resolved'
                        ? 'border-emerald-500 bg-emerald-500/10 text-emerald-400'
                        : 'border-white/10 text-[#A0A0A0] hover:border-white/20'
                    }`}
                  >
                    <CheckCircle className="w-4 h-4" />
                    Resuelto
                  </button>
                  <button
                    onClick={() => setResolveStatus('dismissed')}
                    className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border text-sm font-medium transition-colors ${
                      resolveStatus === 'dismissed'
                        ? 'border-[#606060] bg-white/5 text-[#A0A0A0]'
                        : 'border-white/10 text-[#A0A0A0] hover:border-white/20'
                    }`}
                  >
                    <XCircle className="w-4 h-4" />
                    Descartar
                  </button>
                </div>

                <div>
                  <label className="block text-sm text-[#A0A0A0] mb-2">Nota del administrador (opcional)</label>
                  <textarea
                    value={adminNote}
                    onChange={(e) => setAdminNote(e.target.value)}
                    placeholder="Agrega una nota sobre esta acción..."
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg p-3 text-[#F5F5F5] text-sm resize-none focus:outline-none focus:border-[#D92B2B] transition-colors"
                    rows={3}
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <button
                  onClick={() => { setResolveModal({ open: false, report: null }); setAdminNote(''); }}
                  className="px-4 py-2 text-sm text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleResolveReport}
                  disabled={resolving}
                  className="px-4 py-2 text-sm bg-[#D92B2B] text-white rounded-lg hover:bg-[#F03C3C] transition-colors disabled:opacity-50"
                >
                  {resolving ? 'Guardando...' : 'Confirmar'}
                </button>
              </div>
            </div>
          </div>
        )}

        {categoryModal.open && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
            <div className="bg-[#121212] border border-white/10 rounded-xl p-6 w-full max-w-md">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-[#F5F5F5]">
                  {categoryModal.edit ? 'Editar categoría' : 'Nueva categoría'}
                </h3>
                <button
                  onClick={() => { setCategoryModal({ open: false, edit: null }); setCategoryName(''); setCategoryDesc(''); }}
                  className="p-1 text-[#606060] hover:text-[#F5F5F5] transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4 mb-6">
                <div>
                  <label className="block text-sm text-[#A0A0A0] mb-2">Nombre</label>
                  <input
                    type="text"
                    value={categoryName}
                    onChange={(e) => setCategoryName(e.target.value)}
                    placeholder="Nombre de la categoría"
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-[#F5F5F5] text-sm focus:outline-none focus:border-[#D92B2B] transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-sm text-[#A0A0A0] mb-2">Descripción</label>
                  <textarea
                    value={categoryDesc}
                    onChange={(e) => setCategoryDesc(e.target.value)}
                    placeholder="Descripción de la categoría (opcional)"
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-[#F5F5F5] text-sm resize-none focus:outline-none focus:border-[#D92B2B] transition-colors"
                    rows={3}
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <button
                  onClick={() => { setCategoryModal({ open: false, edit: null }); setCategoryName(''); setCategoryDesc(''); }}
                  className="px-4 py-2 text-sm text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleCategorySave}
                  disabled={!categoryName.trim() || categorySaving}
                  className="flex items-center gap-2 px-4 py-2 text-sm bg-[#D92B2B] text-white rounded-lg hover:bg-[#F03C3C] transition-colors disabled:opacity-50"
                >
                  {categorySaving ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  {categoryModal.edit ? 'Guardar cambios' : 'Crear categoría'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
