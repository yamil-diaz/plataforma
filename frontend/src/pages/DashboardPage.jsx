import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { Pencil, Trash2, Plus, FileArchive, X, Users, BookOpen, ShieldAlert, CheckCircle, Clock, Settings, Video, Trophy, QrCode, Star, Wallet, Banknote } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || '/api';

export default function DashboardPage() {
  const { user } = useAuth();
  const [books, setBooks] = useState([]);
  const [courses, setCourses] = useState([]);
  const [pendingBooks, setPendingBooks] = useState([]);
  const [usersList, setUsersList] = useState([]);
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('books');
  const [earnings, setEarnings] = useState(null);
  const [withdrawForm, setWithdrawForm] = useState({ amount: '', method: 'bank_transfer', account_details: '' });
  const [withdrawMsg, setWithdrawMsg] = useState('');
  const [adminWithdrawals, setAdminWithdrawals] = useState([]);

  // Modal Edit state (Books)
  const [editingBook, setEditingBook] = useState(null);
  const [editForm, setEditForm] = useState({ title: '', author_name: '', category: '', price: 0, rental_price: 0 });

  // Modal Edit state (Courses)
  const [editingCourse, setEditingCourse] = useState(null);
  const [editCourseForm, setEditCourseForm] = useState({ title: '', description: '', instructor: '', category: '', reward_amount: 50 });

  const isAuthor = user?.role === 'autor' || user?.role === 'admin';

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'books') {
        const endpoint = user?.role === 'admin' ? `${API}/books` : `${API}/users/me/books`;
        const { data } = await axios.get(endpoint, { withCredentials: true });
        setBooks(data);
      } else if (activeTab === 'courses' && user?.role === 'admin') {
        const { data } = await axios.get(`${API}/courses`, { withCredentials: true });
        setCourses(data);
      } else if (activeTab === 'users' && user?.role === 'admin') {
        const { data } = await axios.get(`${API}/users`, { withCredentials: true });
        setUsersList(data);
      } else if (activeTab === 'pending' && user?.role === 'admin') {
        const { data } = await axios.get(`${API}/books/pending`, { withCredentials: true });
        setPendingBooks(data);
      } else if (activeTab === 'settings' && user?.role === 'admin') {
        const { data } = await axios.get(`${API}/settings`, { withCredentials: true });
        setSettings(data);
      } else if (activeTab === 'commerce' && user?.role === 'admin') {
        try {
          const { data } = await axios.get(`${API}/admin/commerce/stats`, { withCredentials: true });
          document.getElementById('commerce-total-sales').textContent = data.total_sales || 0;
          document.getElementById('commerce-revenue').textContent = `S/ ${(data.total_revenue || 0).toFixed(2)}`;
          document.getElementById('commerce-pending').textContent = data.pending_orders || 0;
          document.getElementById('commerce-rejected').textContent = data.rejected_orders || 0;
        } catch (err) {
          console.error('Error loading commerce stats:', err);
        }
        try {
          const { data } = await axios.get(`${API}/admin/withdrawals`, { withCredentials: true });
          setAdminWithdrawals(data.withdrawals || []);
        } catch (err) {
          console.error('Error loading withdrawals:', err);
        }
      } else if (activeTab === 'earnings' && isAuthor) {
        try {
          const { data } = await axios.get(`${API}/author/earnings`, { withCredentials: true });
          setEarnings(data);
        } catch (err) {
          console.error('Error loading earnings:', err);
          setEarnings({ total_sales: 0, requested: 0, available: 0, recent_sales: [], withdrawals: [] });
        }
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleWithdrawSubmit = async (e) => {
    e.preventDefault();
    setWithdrawMsg('');
    try {
      const { data } = await axios.post(`${API}/author/withdrawals`, {
        amount: parseFloat(withdrawForm.amount),
        method: withdrawForm.method,
        account_details: withdrawForm.account_details,
      }, { withCredentials: true });
      setWithdrawMsg(data.message || 'Solicitud enviada');
      setWithdrawForm({ amount: '', method: 'bank_transfer', account_details: '' });
      fetchData();
    } catch (err) {
      setWithdrawMsg(err.response?.data?.detail || 'Error al solicitar el retiro');
    }
  };

  const handleWithdrawDecision = async (id, status) => {
    try {
      await axios.put(`${API}/admin/withdrawals/${id}`, { status }, { withCredentials: true });
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al actualizar');
    }
  };

  const handleDelete = async (bookId) => {
    if (!window.confirm("¿Seguro que deseas eliminar esta publicación? Se quitarán también sus compras asociadas.")) return;
    try {
      await axios.delete(`${API}/books/${bookId}`, { withCredentials: true });
      setBooks(books.filter(b => b.id !== bookId && b._id !== String(bookId)));
    } catch (error) {
      alert(error.response?.data?.detail || "Error al eliminar el libro.");
    }
  };

  const handleDeleteCourse = async (courseId) => {
    if (!window.confirm("¿Seguro que deseas eliminar este curso?")) return;
    try {
      await axios.delete(`${API}/courses/${courseId}`, { withCredentials: true });
      setCourses(courses.filter(c => c.id !== courseId));
    } catch (error) {
      alert(error.response?.data?.detail || "Error al eliminar el curso.");
    }
  };

  const handleApprove = async (bookId) => {
    try {
      await axios.put(`${API}/books/${bookId}/approve`, {}, { withCredentials: true });
      setPendingBooks(pendingBooks.filter(b => b.id !== bookId));
    } catch (error) {
      alert(error.response?.data?.detail || "Error al aprobar.");
    }
  };

  const handleReject = async (bookId) => {
    if (!window.confirm("¿Rechazar y eliminar esta publicación?")) return;
    try {
      await axios.delete(`${API}/books/${bookId}/reject`, { withCredentials: true });
      setPendingBooks(pendingBooks.filter(b => b.id !== bookId));
    } catch (error) {
      alert(error.response?.data?.detail || "Error al rechazar.");
    }
  };

  const handleBanToggle = async (userId) => {
    try {
      const { data } = await axios.put(`${API}/users/${userId}/ban`, {}, { withCredentials: true });
      setUsersList(usersList.map(u => u.id === userId ? { ...u, is_banned: data.is_banned } : u));
    } catch (error) {
      alert(error.response?.data?.detail || 'Error al actualizar baneo');
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    try {
      await axios.put(`${API}/users/${userId}/role`, { role: newRole }, { withCredentials: true });
      setUsersList(usersList.map(u => u.id === userId ? { ...u, role: newRole } : u));
    } catch (error) {
      alert(error.response?.data?.detail || 'Error al cambiar rol');
    }
  };

  const openEditModal = (book) => {
    setEditingBook(book);
    setEditForm({
      title: book.title,
      author_name: book.author_name,
      category: book.category,
      price: book.price || 0,
      rental_price: book.rental_price || 0,
      cover_image: null
    });
  };

  const closeEditModal = () => {
    setEditingBook(null);
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    try {
      const formData = new FormData();
      formData.append('title', editForm.title);
      formData.append('author_name', editForm.author_name);
      formData.append('category', editForm.category);
      formData.append('price', editForm.price);
      formData.append('rental_price', editForm.rental_price || 0);
      if (editForm.cover_image) {
        formData.append('cover_image', editForm.cover_image);
      }
      
      await axios.put(`${API}/books/${editingBook.id}`, formData, { withCredentials: true });
      
      setBooks(books.map(b => b.id === editingBook.id ? { ...b, ...editForm } : b));
      closeEditModal();
      alert("Publicación actualizada con éxito");
    } catch (error) {
      alert("Error al actualizar la publicación.");
      console.error(error);
    }
  };

  const openEditCourseModal = (course) => {
    setEditingCourse(course);
    setEditCourseForm({
      title: course.title,
      description: course.description,
      instructor: course.instructor,
      category: course.category,
      reward_amount: course.reward_amount,
      cover_image: null
    });
  };

  const closeEditCourseModal = () => {
    setEditingCourse(null);
  };

  const handleEditCourseSubmit = async (e) => {
    e.preventDefault();
    try {
      const formData = new FormData();
      formData.append('title', editCourseForm.title);
      formData.append('description', editCourseForm.description);
      formData.append('instructor', editCourseForm.instructor);
      formData.append('category', editCourseForm.category);
      formData.append('reward_amount', editCourseForm.reward_amount);
      if (editCourseForm.cover_image) {
        formData.append('cover_image', editCourseForm.cover_image);
      }
      
      await axios.put(`${API}/courses/${editingCourse.id}`, formData, { withCredentials: true });
      
      setCourses(courses.map(c => c.id === editingCourse.id ? { ...c, ...editCourseForm } : c));
      closeEditCourseModal();
      alert("Curso actualizado con éxito");
    } catch (error) {
      alert("Error al actualizar el curso.");
      console.error(error);
    }
  };

  const ROLE_LABELS = { admin: 'Admin', autor: 'Vendedor', user: 'Comprador' };
  const totalAutores = usersList.filter(u => u.role === 'autor').length;
  const totalLectores = usersList.filter(u => u.role === 'user').length;
  const totalAdmins = usersList.filter(u => u.role === 'admin').length;
  const totalBanned = usersList.filter(u => u.is_banned).length;
  const myRoleLabel = ROLE_LABELS[user?.role] || 'Comprador';

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-24">
      <Navbar />
      <main className="max-w-6xl mx-auto px-6 pt-12">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-8 gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-white font-['Outfit']">
                {user?.role === 'admin'
                  ? 'Panel de Administración'
                  : user?.role === 'autor'
                    ? 'Panel de Vendedor'
                    : 'Panel del Comprador'}
              </h1>
              <span
                className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${
                  user?.role === 'admin'
                    ? 'bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/30'
                    : user?.role === 'autor'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                }`}
              >
                {myRoleLabel}
              </span>
            </div>
            <p className="text-sm text-[#A0A0A0] mt-1">
              {user?.role === 'admin'
                ? 'Gestiona todo el catálogo de libros y los usuarios de la plataforma.'
                : user?.role === 'autor'
                  ? 'Gestiona tus publicaciones como vendedor y consulta tus ganancias.'
                  : 'Tu cuenta es de comprador: lees, ganas Rayos y participas. Un admin puede darte el rol Vendedor para publicar.'}
            </p>
          </div>

          <div className="flex items-center gap-3">
            {user?.role !== 'user' && (
              <Link to="/admin/new-book" className="flex items-center gap-2 bg-[#D92B2B] hover:bg-[#F03C3C] text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors">
                <Plus className="w-4 h-4" /> Nueva Publicación
              </Link>
            )}
            {user?.role === 'admin' && (
              <>
                <Link to="/admin/new-course" className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors shadow-lg">
                  <Video className="w-4 h-4" /> Nuevo Curso
                </Link>
                <Link to="/admin/competitions/new" className="flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors shadow-lg">
                  <Trophy className="w-4 h-4" /> Nueva Competencia
                </Link>
                <Link to="/admin/import" className="flex items-center gap-2 bg-[#121212] border border-white/10 hover:border-white/20 text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors shadow-lg">
                  <FileArchive className="w-4 h-4" /> ZIP
                </Link>
                <Link to="/admin/qr-codes" className="flex items-center gap-2 bg-[#121212] border border-white/10 hover:border-white/20 text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors shadow-lg">
                  <QrCode className="w-4 h-4" /> Códigos QR
                </Link>
                <Link to="/admin/featured-books" className="flex items-center gap-2 bg-[#121212] border border-[#D4AF37]/30 hover:border-[#D4AF37]/50 text-[#D4AF37] px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors shadow-lg">
                  <Star className="w-4 h-4" /> Libros Destacados
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex flex-wrap gap-4 border-b border-white/10 mb-8">
          <button
            onClick={() => setActiveTab('books')}
            className={`pb-3 px-2 text-sm font-semibold transition-colors border-b-2 ${activeTab === 'books' ? 'border-[#D92B2B] text-white' : 'border-transparent text-[#A0A0A0] hover:text-[#F5F5F5]'}`}
          >
            Libros
          </button>
          {isAuthor && (
            <button
              onClick={() => setActiveTab('earnings')}
              className={`pb-3 px-2 text-sm font-semibold transition-colors border-b-2 flex items-center gap-1.5 ${activeTab === 'earnings' ? 'border-[#D4AF37] text-[#D4AF37]' : 'border-transparent text-[#A0A0A0] hover:text-[#F5F5F5]'}`}
            >
              <Wallet className="w-4 h-4" />
              Mis Ganancias
            </button>
          )}
          {user?.role === 'admin' && (
            <>
              <button
                onClick={() => setActiveTab('courses')}
                className={`pb-3 px-2 text-sm font-semibold transition-colors border-b-2 ${activeTab === 'courses' ? 'border-blue-500 text-white' : 'border-transparent text-[#A0A0A0] hover:text-[#F5F5F5]'}`}
              >
                Cursos
              </button>
              <button
                onClick={() => setActiveTab('pending')}
                className={`pb-3 px-2 text-sm font-semibold transition-colors border-b-2 flex items-center gap-1 ${activeTab === 'pending' ? 'border-orange-500 text-orange-400' : 'border-transparent text-[#A0A0A0] hover:text-[#F5F5F5]'}`}
              >
                Pendientes
              </button>
              <button
                onClick={() => setActiveTab('users')}
                className={`pb-3 px-2 text-sm font-semibold transition-colors border-b-2 ${activeTab === 'users' ? 'border-[#D92B2B] text-white' : 'border-transparent text-[#A0A0A0] hover:text-[#F5F5F5]'}`}
              >
                Gestión de Usuarios
              </button>
              <button
                onClick={() => setActiveTab('commerce')}
                className={`pb-3 px-2 text-sm font-semibold transition-colors border-b-2 ${activeTab === 'commerce' ? 'border-[#D4AF37] text-[#D4AF37]' : 'border-transparent text-[#A0A0A0] hover:text-[#F5F5F5]'}`}
              >
                Comercio
              </button>
            </>
          )}
        </div>

        {loading ? (
          <div className="text-center text-[#A0A0A0] py-20">Cargando datos...</div>
        ) : activeTab === 'earnings' ? (
          /* PESTAÑA GANANCIAS (AUTOR/ADMIN) */
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-[#121212] border border-white/10 p-5 rounded-xl shadow-lg">
                <div className="flex items-center gap-3 text-[#A0A0A0] mb-2">
                  <Banknote className="w-5 h-5 text-emerald-400" />
                  <span className="text-sm font-semibold uppercase tracking-wider">Ventas totales</span>
                </div>
                <div className="text-3xl font-bold text-white">S/ {(earnings?.total_sales || 0).toFixed(2)}</div>
              </div>
              <div className="bg-[#121212] border border-white/10 p-5 rounded-xl shadow-lg">
                <div className="flex items-center gap-3 text-[#A0A0A0] mb-2">
                  <Wallet className="w-5 h-5 text-[#D4AF37]" />
                  <span className="text-sm font-semibold uppercase tracking-wider">Disponible para retiro</span>
                </div>
                <div className="text-3xl font-bold text-[#D4AF37]">S/ {(earnings?.available || 0).toFixed(2)}</div>
              </div>
              <div className="bg-[#121212] border border-white/10 p-5 rounded-xl shadow-lg">
                <div className="flex items-center gap-3 text-[#A0A0A0] mb-2">
                  <Clock className="w-5 h-5 text-blue-400" />
                  <span className="text-sm font-semibold uppercase tracking-wider">Órdenes / ítems</span>
                </div>
                <div className="text-3xl font-bold text-white">{earnings?.orders_count || 0} / {earnings?.items_count || 0}</div>
              </div>
            </div>

            <div className="bg-[#121212] border border-white/10 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <Wallet className="w-5 h-5 text-[#D4AF37]" /> Solicitar retiro
              </h3>
              {withdrawMsg && (
                <div className="mb-4 p-3 rounded-lg text-sm bg-emerald-950/20 border border-emerald-500/30 text-emerald-400">
                  {withdrawMsg}
                </div>
              )}
              <form onSubmit={handleWithdrawSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Monto (S/)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="1"
                    required
                    value={withdrawForm.amount}
                    onChange={(e) => setWithdrawForm({ ...withdrawForm, amount: e.target.value })}
                    placeholder="Ej. 50.00"
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-[#F5F5F5] focus:border-[#D4AF37] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Método</label>
                  <select
                    value={withdrawForm.method}
                    onChange={(e) => setWithdrawForm({ ...withdrawForm, method: e.target.value })}
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-[#F5F5F5] focus:border-[#D4AF37] focus:outline-none"
                  >
                    <option value="bank_transfer">Transferencia bancaria</option>
                    <option value="yape">Yape</option>
                    <option value="plin">Plin</option>
                    <option value="paypal">PayPal</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Datos de cuenta</label>
                  <input
                    type="text"
                    required
                    value={withdrawForm.account_details}
                    onChange={(e) => setWithdrawForm({ ...withdrawForm, account_details: e.target.value })}
                    placeholder="CCI, número de cuenta, email PayPal..."
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-[#F5F5F5] focus:border-[#D4AF37] focus:outline-none"
                  />
                </div>
                <div className="md:col-span-3">
                  <button
                    type="submit"
                    className="bg-[#D4AF37] hover:bg-[#F2D06B] text-black font-bold px-6 py-3 rounded-lg transition-colors"
                  >
                    Enviar solicitud de retiro
                  </button>
                  <p className="text-xs text-[#A0A0A0] mt-2">
                    Un administrador revisará tu solicitud y procesará el pago. Disponible: S/ {(earnings?.available || 0).toFixed(2)}
                  </p>
                </div>
              </form>
            </div>

            <div className="bg-[#121212] border border-white/10 rounded-xl overflow-hidden">
              <div className="p-4 border-b border-white/10">
                <h3 className="text-lg font-bold text-white">Historial de retiros</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="bg-[#1A1A1A] text-[#A0A0A0] text-xs uppercase">
                      <th className="p-3">Fecha</th>
                      <th className="p-3">Monto</th>
                      <th className="p-3">Método</th>
                      <th className="p-3">Estado</th>
                      <th className="p-3">Nota</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(earnings?.withdrawals || []).map(w => (
                      <tr key={w.id} className="border-b border-white/5">
                        <td className="p-3 text-[#A0A0A0] text-sm">{(w.created_at || '').slice(0, 10)}</td>
                        <td className="p-3 text-white font-semibold">S/ {parseFloat(w.amount).toFixed(2)}</td>
                        <td className="p-3 text-[#A0A0A0] text-sm">{w.method}</td>
                        <td className="p-3">
                          <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${
                            w.status === 'paid' ? 'bg-emerald-500/10 text-emerald-400' :
                            w.status === 'approved' ? 'bg-blue-500/10 text-blue-400' :
                            w.status === 'rejected' ? 'bg-red-500/10 text-red-400' :
                            'bg-yellow-500/10 text-yellow-400'
                          }`}>
                            {w.status === 'pending' ? 'Pendiente' :
                             w.status === 'approved' ? 'Aprobado' :
                             w.status === 'rejected' ? 'Rechazado' : 'Pagado'}
                          </span>
                        </td>
                        <td className="p-3 text-[#A0A0A0] text-sm">{w.admin_note || '—'}</td>
                      </tr>
                    ))}
                    {(earnings?.withdrawals || []).length === 0 && (
                      <tr><td colSpan={5} className="p-6 text-center text-[#A0A0A0]">Sin solicitudes de retiro aún</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="bg-[#121212] border border-white/10 rounded-xl overflow-hidden">
              <div className="p-4 border-b border-white/10">
                <h3 className="text-lg font-bold text-white">Ventas recientes</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="bg-[#1A1A1A] text-[#A0A0A0] text-xs uppercase">
                      <th className="p-3">Libro</th>
                      <th className="p-3">Monto</th>
                      <th className="p-3">Moneda</th>
                      <th className="p-3">Orden</th>
                      <th className="p-3">Fecha</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(earnings?.recent_sales || []).map((s, i) => (
                      <tr key={i} className="border-b border-white/5">
                        <td className="p-3 text-white text-sm">{s.title}</td>
                        <td className="p-3 text-[#D4AF37] font-semibold">S/ {parseFloat(s.subtotal).toFixed(2)}</td>
                        <td className="p-3 text-[#A0A0A0] text-sm">{s.currency}</td>
                        <td className="p-3 text-[#A0A0A0] text-sm">{s.order_number}</td>
                        <td className="p-3 text-[#A0A0A0] text-sm">{(s.created_at || '').slice(0, 10)}</td>
                      </tr>
                    ))}
                    {(earnings?.recent_sales || []).length === 0 && (
                      <tr><td colSpan={5} className="p-6 text-center text-[#A0A0A0]">Aún no tienes ventas registradas</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : activeTab === 'books' ? (
          /* PESTAÑA LIBROS */
          books.length === 0 ? (
            <div className="bg-[#121212] border border-white/5 rounded-xl p-12 text-center">
              <p className="text-[#A0A0A0] mb-4">
                {user?.role === 'user'
                  ? 'Todavía no tienes publicaciones. Tu rol actual es Comprador.'
                  : 'No hay publicaciones aún.'}
              </p>
              {user?.role !== 'user' && (
                <Link to="/admin/new-book" className="text-[#D92B2B] hover:underline font-semibold">Comienza a publicar ahora</Link>
              )}
            </div>
          ) : (
            <div className="bg-[#121212] border border-white/10 rounded-xl overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse min-w-[800px]">
                  <thead>
                    <tr className="bg-[#1A1A1A] border-b border-white/10 text-[#A0A0A0] text-xs uppercase tracking-wider">
                      <th className="p-4 font-semibold">Título y Portada</th>
                      <th className="p-4 font-semibold">Autor</th>
                      <th className="p-4 font-semibold text-center">Estado</th>
                      <th className="p-4 font-semibold text-center">Interacciones</th>
                      <th className="p-4 font-semibold text-right">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {books.map(book => (
                      <tr key={book.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                        <td className="p-4 text-white font-medium">
                          <div className="flex items-center gap-3">
                            <img src={book.cover_image_url || 'https://via.placeholder.com/50'} alt={book.title} className="w-12 h-16 object-cover rounded-md border border-white/10 shadow-md" />
                            <span className="line-clamp-2 max-w-[200px]">{book.title}</span>
                          </div>
                        </td>
                        <td className="p-4 text-[#A0A0A0] text-sm">{book.author_name}</td>
                        <td className="p-4 text-center">
                          {book.published === 1 ? (
                            <span className="bg-emerald-500/10 text-emerald-400 px-2 py-1 rounded-full text-[10px] font-bold uppercase border border-emerald-500/20">Aprobado</span>
                          ) : (
                            <span className="bg-orange-500/10 text-orange-400 px-2 py-1 rounded-full text-[10px] font-bold uppercase border border-orange-500/20">Pendiente</span>
                          )}
                        </td>
                        <td className="p-4 text-[#A0A0A0] text-sm text-center">
                          <span className="text-white font-medium">{book.views}</span> vis / <span className="text-white font-medium">{book.likes}</span> likes
                        </td>
                        <td className="p-4 text-right">
                          <div className="flex justify-end gap-2">
                            <button onClick={() => openEditModal(book)} className="flex items-center gap-1.5 px-3 py-1.5 bg-[#D4AF37]/10 text-[#D4AF37] hover:bg-[#D4AF37]/20 border border-[#D4AF37]/30 rounded-lg transition-colors text-xs font-semibold">
                              <Pencil className="w-3.5 h-3.5" /> Editar
                            </button>
                            <button onClick={() => handleDelete(book.id)} className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/30 rounded-lg transition-colors text-xs font-semibold">
                              <Trash2 className="w-3.5 h-3.5" /> Borrar
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )
        ) : activeTab === 'courses' && user?.role === 'admin' ? (
          /* PESTAÑA CURSOS (SOLO ADMIN) */
          courses.length === 0 ? (
            <div className="bg-[#121212] border border-white/5 rounded-xl p-12 text-center">
              <p className="text-[#A0A0A0] mb-4">No hay cursos aún.</p>
              <Link to="/admin/new-course" className="text-blue-500 hover:underline font-semibold">Comienza a publicar cursos ahora</Link>
            </div>
          ) : (
            <div className="bg-[#121212] border border-white/10 rounded-xl overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse min-w-[800px]">
                  <thead>
                    <tr className="bg-[#1A1A1A] border-b border-white/10 text-[#A0A0A0] text-xs uppercase tracking-wider">
                      <th className="p-4 font-semibold">Título y Portada</th>
                      <th className="p-4 font-semibold">Instructor</th>
                      <th className="p-4 font-semibold">Categoría</th>
                      <th className="p-4 font-semibold text-center">Rayos</th>
                      <th className="p-4 font-semibold text-right">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {courses.map(course => (
                      <tr key={course.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                        <td className="p-4 text-white font-medium">
                          <div className="flex items-center gap-3">
                            <img src={course.cover_url || 'https://via.placeholder.com/50'} alt={course.title} className="w-16 h-12 object-cover rounded-md border border-white/10 shadow-md" />
                            <span className="line-clamp-2 max-w-[200px]">{course.title}</span>
                          </div>
                        </td>
                        <td className="p-4 text-[#A0A0A0] text-sm">{course.instructor}</td>
                        <td className="p-4 text-[#A0A0A0] text-sm"><span className="bg-white/5 px-2 py-1 rounded">{course.category}</span></td>
                        <td className="p-4 text-center text-[#D4AF37] font-bold">+{course.reward_amount}</td>
                        <td className="p-4 text-right">
                          <div className="flex justify-end gap-2">
                            <button onClick={() => openEditCourseModal(course)} className="flex items-center gap-1.5 px-3 py-1.5 bg-[#D4AF37]/10 text-[#D4AF37] hover:bg-[#D4AF37]/20 border border-[#D4AF37]/30 rounded-lg transition-colors text-xs font-semibold">
                              <Pencil className="w-3.5 h-3.5" /> Editar
                            </button>
                            <button onClick={() => handleDeleteCourse(course.id)} className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/30 rounded-lg transition-colors text-xs font-semibold">
                              <Trash2 className="w-3.5 h-3.5" /> Borrar
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )
        ) : activeTab === 'pending' && user?.role === 'admin' ? (
          /* PESTAÑA PENDIENTES (SOLO ADMIN) */
          pendingBooks.length === 0 ? (
             <div className="bg-[#121212] border border-white/5 rounded-xl p-12 text-center text-[#A0A0A0]">
               No hay publicaciones pendientes de aprobación.
             </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {pendingBooks.map(book => (
                <div key={book.id} className="bg-[#121212] border border-orange-500/30 p-4 rounded-xl shadow-lg flex flex-col gap-4 relative overflow-hidden">
                  <div className="absolute top-0 right-0 bg-orange-500 text-white text-[10px] font-bold px-3 py-1 uppercase rounded-bl-xl shadow-lg z-10 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> Revisión Requerida
                  </div>
                  <div className="flex gap-4 items-start">
                    <img src={book.cover_image_url} alt={book.title} className="w-20 h-28 object-cover rounded shadow-md border border-white/10" />
                    <div>
                      <h3 className="text-white font-bold text-lg leading-tight">{book.title}</h3>
                      <p className="text-[#A0A0A0] text-sm mt-1">{book.author_name}</p>
                      <span className="inline-block mt-2 bg-white/10 text-[#F5F5F5] px-2 py-0.5 rounded text-[10px] uppercase">{book.category}</span>
                    </div>
                  </div>
                  <div className="flex gap-2 mt-auto">
                    <button onClick={() => handleApprove(book.id)} className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white py-2 rounded-lg text-sm font-semibold transition-colors flex items-center justify-center gap-1">
                      <CheckCircle className="w-4 h-4" /> Aprobar
                    </button>
                    <button onClick={() => handleReject(book.id)} className="flex-1 bg-transparent hover:bg-red-500/10 text-red-500 border border-red-500/30 py-2 rounded-lg text-sm font-semibold transition-colors flex items-center justify-center gap-1">
                      <X className="w-4 h-4" /> Rechazar
                    </button>
                  </div>
                </div>
              ))}
            </div>
           )
        ) : activeTab === 'commerce' && user?.role === 'admin' ? (
          /* PESTAÑA COMERCIO */
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-[#121212] border border-white/10 p-5 rounded-xl shadow-lg">
                <p className="text-[#A0A0A0] text-sm font-semibold uppercase tracking-wider mb-2">Ventas Totales</p>
                <p className="text-3xl font-bold text-white" id="commerce-total-sales">—</p>
              </div>
              <div className="bg-[#121212] border border-white/10 p-5 rounded-xl shadow-lg">
                <p className="text-[#A0A0A0] text-sm font-semibold uppercase tracking-wider mb-2">Ingresos (PEN)</p>
                <p className="text-3xl font-bold text-[#D4AF37]" id="commerce-revenue">—</p>
              </div>
              <div className="bg-[#121212] border border-white/10 p-5 rounded-xl shadow-lg">
                <p className="text-[#A0A0A0] text-sm font-semibold uppercase tracking-wider mb-2">Pendientes</p>
                <p className="text-3xl font-bold text-yellow-400" id="commerce-pending">—</p>
              </div>
              <div className="bg-[#121212] border border-white/10 p-5 rounded-xl shadow-lg">
                <p className="text-[#A0A0A0] text-sm font-semibold uppercase tracking-wider mb-2">Rechazados</p>
                <p className="text-3xl font-bold text-red-400" id="commerce-rejected">—</p>
              </div>
            </div>
            <div className="bg-[#121212] border border-white/10 rounded-xl overflow-hidden">
              <div className="p-4 border-b border-white/10">
                <h3 className="text-lg font-bold text-white">Solicitudes de retiro de autores</h3>
                <p className="text-xs text-[#A0A0A0] mt-1">Aprueba o rechaza las solicitudes de pago a autores</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="bg-[#1A1A1A] text-[#A0A0A0] text-xs uppercase">
                      <th className="p-3">Autor</th>
                      <th className="p-3">Monto</th>
                      <th className="p-3">Método</th>
                      <th className="p-3">Datos</th>
                      <th className="p-3">Estado</th>
                      <th className="p-3">Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {adminWithdrawals.map(w => (
                      <tr key={w.id} className="border-b border-white/5">
                        <td className="p-3">
                          <div className="text-white text-sm font-medium">{w.name}</div>
                          <div className="text-[#A0A0A0] text-xs">{w.email}</div>
                        </td>
                        <td className="p-3 text-[#D4AF37] font-bold">S/ {parseFloat(w.amount).toFixed(2)}</td>
                        <td className="p-3 text-[#A0A0A0] text-sm">{w.method}</td>
                        <td className="p-3 text-[#A0A0A0] text-xs max-w-[160px] truncate" title={w.account_details}>{w.account_details}</td>
                        <td className="p-3">
                          <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${
                            w.status === 'paid' ? 'bg-emerald-500/10 text-emerald-400' :
                            w.status === 'approved' ? 'bg-blue-500/10 text-blue-400' :
                            w.status === 'rejected' ? 'bg-red-500/10 text-red-400' :
                            'bg-yellow-500/10 text-yellow-400'
                          }`}>
                            {w.status === 'pending' ? 'Pendiente' :
                             w.status === 'approved' ? 'Aprobado' :
                             w.status === 'rejected' ? 'Rechazado' : 'Pagado'}
                          </span>
                        </td>
                        <td className="p-3">
                          {w.status === 'pending' && (
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleWithdrawDecision(w.id, 'approved')}
                                className="px-3 py-1.5 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-lg text-xs font-semibold"
                              >
                                Aprobar
                              </button>
                              <button
                                onClick={() => handleWithdrawDecision(w.id, 'rejected')}
                                className="px-3 py-1.5 bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/30 rounded-lg text-xs font-semibold"
                              >
                                Rechazar
                              </button>
                            </div>
                          )}
                          {w.status === 'approved' && (
                            <button
                              onClick={() => handleWithdrawDecision(w.id, 'paid')}
                              className="px-3 py-1.5 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 border border-blue-500/30 rounded-lg text-xs font-semibold"
                            >
                              Marcar pagado
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                    {adminWithdrawals.length === 0 && (
                      <tr><td colSpan={6} className="p-6 text-center text-[#A0A0A0]">No hay solicitudes de retiro</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="bg-[#121212] border border-white/10 rounded-xl p-6">
              <p className="text-white font-bold mb-4">Órdenes Recientes</p>
              <p className="text-[#A0A0A0] text-sm">
                Carga de estadísticas de comercio desde <code className="bg-white/5 px-1 rounded">/api/admin/commerce/stats</code>.
              </p>
            </div>
          </div>
        ) : (
          /* PESTAÑA USUARIOS (SOLO ADMIN) */
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-[#121212] border border-white/10 p-5 rounded-xl shadow-lg">
                <div className="flex items-center gap-3 text-[#A0A0A0] mb-2">
                  <Users className="w-5 h-5 text-blue-400" />
                  <span className="text-sm font-semibold uppercase tracking-wider">Total Usuarios</span>
                </div>
                <div className="text-3xl font-bold text-white">{usersList.length}</div>
              </div>
              <div className="bg-[#121212] border border-white/10 p-5 rounded-xl shadow-lg">
                <div className="flex items-center gap-3 text-[#A0A0A0] mb-2">
                  <BookOpen className="w-5 h-5 text-emerald-400" />
                  <span className="text-sm font-semibold uppercase tracking-wider">Autores (rol)</span>
                </div>
                <div className="text-3xl font-bold text-white">{totalAutores}</div>
              </div>
              <div className="bg-[#121212] border border-white/10 p-5 rounded-xl shadow-lg">
                <div className="flex items-center gap-3 text-[#A0A0A0] mb-2">
                  <Users className="w-5 h-5 text-blue-400" />
                  <span className="text-sm font-semibold uppercase tracking-wider">Compradores (rol)</span>
                </div>
                <div className="text-3xl font-bold text-white">{totalLectores}</div>
              </div>
              <div className="bg-[#121212] border border-white/10 p-5 rounded-xl shadow-lg">
                <div className="flex items-center gap-3 text-[#A0A0A0] mb-2">
                  <ShieldAlert className="w-5 h-5 text-[#D4AF37]" />
                  <span className="text-sm font-semibold uppercase tracking-wider">Admins</span>
                </div>
                <div className="text-3xl font-bold text-white">{totalAdmins}</div>
              </div>
              <div className="bg-[#121212] border border-white/10 p-5 rounded-xl shadow-lg">
                <div className="flex items-center gap-3 text-[#A0A0A0] mb-2">
                  <X className="w-5 h-5 text-red-500" />
                  <span className="text-sm font-semibold uppercase tracking-wider">Baneados</span>
                </div>
                <div className="text-3xl font-bold text-white">{totalBanned}</div>
              </div>
            </div>

            <div className="bg-[#121212] border border-white/10 rounded-xl overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse min-w-[800px]">
                  <thead>
                    <tr className="bg-[#1A1A1A] border-b border-white/10 text-[#A0A0A0] text-xs uppercase tracking-wider">
                      <th className="p-4 font-semibold">Usuario</th>
                      <th className="p-4 font-semibold">Email</th>
                      <th className="p-4 font-semibold">Rol</th>
                      <th className="p-4 font-semibold text-center">Libros Subidos</th>
                      <th className="p-4 font-semibold text-center">Estado</th>
                      <th className="p-4 font-semibold text-right">Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usersList.map(u => (
                      <tr key={u.id} className={`border-b border-white/5 hover:bg-white/[0.02] transition-colors ${u.is_banned ? 'opacity-70' : ''}`}>
                        <td className="p-4 text-white font-medium">{u.name}</td>
                        <td className="p-4 text-[#A0A0A0] text-sm">{u.email}</td>
                        <td className="p-4 text-sm">
                          <div className="flex flex-col gap-1">
                            <span
                              className={`inline-flex self-start px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${
                                u.role === 'admin'
                                  ? 'bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/30'
                                  : u.role === 'autor'
                                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                                    : 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                              }`}
                            >
                              {ROLE_LABELS[u.role] || u.role}
                            </span>
                            <select
                              value={u.role}
                              onChange={(e) => handleRoleChange(u.id, e.target.value)}
                              disabled={u.role === 'admin'}
                              title="Cambiar rol del usuario"
                              className={`px-2 py-1 rounded text-xs font-semibold uppercase border outline-none cursor-pointer ${u.role === 'admin' ? 'bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/20 opacity-80 cursor-not-allowed' : 'bg-white/5 text-[#A0A0A0] border-white/10 hover:border-white/30'}`}
                            >
                              <option value="user">Comprador</option>
                              <option value="autor">Vendedor</option>
                              <option value="admin">Admin</option>
                            </select>
                          </div>
                        </td>
                        <td className="p-4 text-[#A0A0A0] text-sm text-center font-medium">
                          {u.books_count > 0 ? <span className="text-emerald-400">{u.books_count}</span> : '0'}
                        </td>
                        <td className="p-4 text-center">
                          {u.is_banned 
                            ? <span className="bg-red-500/10 text-red-500 px-2 py-1 rounded text-xs font-bold uppercase">Baneado</span>
                            : <span className="bg-emerald-500/10 text-emerald-400 px-2 py-1 rounded text-xs font-bold uppercase">Activo</span>
                          }
                        </td>
                        <td className="p-4 text-right">
                          <button 
                            onClick={() => handleBanToggle(u.id)}
                            disabled={u.role === 'admin'}
                            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-colors border ${
                              u.role === 'admin' 
                                ? 'bg-transparent text-[#707070] border-[#303030] cursor-not-allowed'
                                : u.is_banned 
                                  ? 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border-emerald-500/30'
                                  : 'bg-red-500/10 text-red-500 hover:bg-red-500/20 border-red-500/30'
                            }`}
                          >
                            {u.role === 'admin' ? 'Intocable' : u.is_banned ? 'Desbanear' : 'Dar Ban'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Edit Modal */}
      {editingBook && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[#121212] border border-white/10 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center p-6 border-b border-white/10">
              <h2 className="text-xl font-bold text-white">Editar Publicación</h2>
              <button onClick={closeEditModal} className="text-[#A0A0A0] hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleEditSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Portada (Opcional)</label>
                <input type="file" accept="image/*" onChange={(e) => setEditForm({...editForm, cover_image: e.target.files[0]})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-2.5 text-[#A0A0A0] focus:border-[#D92B2B] focus:outline-none file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-[#D92B2B]/10 file:text-[#D92B2B] hover:file:bg-[#D92B2B]/20" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Título</label>
                <input required type="text" value={editForm.title} onChange={(e) => setEditForm({...editForm, title: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-2.5 text-[#F5F5F5] focus:border-[#D92B2B] focus:outline-none" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Autor</label>
                <input required type="text" value={editForm.author_name} onChange={(e) => setEditForm({...editForm, author_name: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-2.5 text-[#F5F5F5] focus:border-[#D92B2B] focus:outline-none" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Categoría</label>
                <select value={editForm.category} onChange={(e) => setEditForm({...editForm, category: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-2.5 text-[#F5F5F5] focus:border-[#D92B2B] focus:outline-none">
                  <option value="Ficción">Ficción</option>
                  <option value="Clásicos">Clásicos</option>
                  <option value="Ciencia Ficción">Ciencia Ficción</option>
                  <option value="Terror">Terror</option>
                  <option value="Poesía">Poesía</option>
                  <option value="Historia">Historia</option>
                  <option value="Filosofía">Filosofía</option>
                  <option value="Autoayuda">Autoayuda</option>
                  <option value="Romance">Romance</option>
                  <option value="Aventura">Aventura</option>
                  <option value="Ciencia">Ciencia</option>
                  <option value="Infantil">Infantil</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Precio compra (PEN)</label>
                  <input type="number" step="0.01" min="0" value={editForm.price} onChange={(e) => setEditForm({...editForm, price: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-2.5 text-[#F5F5F5] focus:border-[#D92B2B] focus:outline-none" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Precio alquiler (PEN)</label>
                  <input type="number" step="0.01" min="0" value={editForm.rental_price || 0} onChange={(e) => setEditForm({...editForm, rental_price: e.target.value})} placeholder="0 = 30%" className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-2.5 text-[#F5F5F5] focus:border-[#D92B2B] focus:outline-none" />
                </div>
              </div>
              <div className="pt-4 flex gap-3">
                <button type="button" onClick={closeEditModal} className="flex-1 bg-white/5 hover:bg-white/10 text-white font-semibold py-3 rounded-lg transition-colors">Cancelar</button>
                <button type="submit" className="flex-1 bg-[#D92B2B] hover:bg-[#F03C3C] text-white font-semibold py-3 rounded-lg transition-colors">Guardar Cambios</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT COURSE MODAL */}
      {editingCourse && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#121212] border border-white/10 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-fade-in-up">
            <div className="flex justify-between items-center p-5 border-b border-white/10 bg-[#1A1A1A]">
              <h2 className="text-xl font-bold text-white">Editar Curso</h2>
              <button onClick={closeEditCourseModal} className="text-[#A0A0A0] hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleEditCourseSubmit} className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Miniatura (Opcional)</label>
                <input type="file" accept="image/*" onChange={e => setEditCourseForm({...editCourseForm, cover_image: e.target.files[0]})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-[#A0A0A0] focus:border-blue-500 focus:outline-none file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-500/10 file:text-blue-500 hover:file:bg-blue-500/20" />
              </div>
              
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Título del Curso</label>
                <input required type="text" value={editCourseForm.title} onChange={e => setEditCourseForm({...editCourseForm, title: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none" />
              </div>
              
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Instructor</label>
                <input required type="text" value={editCourseForm.instructor} onChange={e => setEditCourseForm({...editCourseForm, instructor: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none" />
              </div>
              
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Descripción</label>
                <textarea required rows="3" value={editCourseForm.description} onChange={e => setEditCourseForm({...editCourseForm, description: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none"></textarea>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Categoría</label>
                  <input required type="text" value={editCourseForm.category} onChange={e => setEditCourseForm({...editCourseForm, category: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Recompensa (Rayos)</label>
                  <input required type="number" min="0" value={editCourseForm.reward_amount} onChange={e => setEditCourseForm({...editCourseForm, reward_amount: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none" />
                </div>
              </div>
              
              <div className="flex gap-3 pt-4 border-t border-white/10">
                <button type="button" onClick={closeEditCourseModal} className="flex-1 bg-transparent hover:bg-white/5 border border-white/10 text-white font-semibold py-3 rounded-xl transition-colors">
                  Cancelar
                </button>
                <button type="submit" className="flex-1 bg-[#D4AF37] hover:bg-[#F2D06B] text-black font-bold py-3 rounded-xl transition-all shadow-lg">
                  Guardar Cambios
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <Footer />
    </div>
  );
}
