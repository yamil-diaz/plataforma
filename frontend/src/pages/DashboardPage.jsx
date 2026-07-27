import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { Pencil, Trash2, Plus, FileArchive, X, Users, BookOpen, ShieldAlert } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function DashboardPage() {
  const { user } = useAuth();
  const [books, setBooks] = useState([]);
  const [usersList, setUsersList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('books');
  
  // Modal Edit state
  const [editingBook, setEditingBook] = useState(null);
  const [editForm, setEditForm] = useState({ title: '', author_name: '', category: '', price: 0 });

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
      } else if (activeTab === 'users' && user?.role === 'admin') {
        const { data } = await axios.get(`${API}/users`, { withCredentials: true });
        setUsersList(data);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (bookId) => {
    if (!window.confirm("¿Seguro que deseas eliminar esta publicación?")) return;
    try {
      await axios.delete(`${API}/books/${bookId}`, { withCredentials: true });
      setBooks(books.filter(b => b.id !== bookId));
    } catch (error) {
      alert("Error al eliminar el libro.");
    }
  };

  const handleBanToggle = async (targetId) => {
    if (!window.confirm("¿Estás seguro de cambiar el estado de baneo de este usuario?")) return;
    try {
      const { data } = await axios.put(`${API}/users/${targetId}/ban`, {}, { withCredentials: true });
      setUsersList(usersList.map(u => u.id === targetId ? { ...u, is_banned: data.is_banned } : u));
    } catch (error) {
      alert(error.response?.data?.detail || "Error al banear usuario");
    }
  };

  const openEditModal = (book) => {
    setEditingBook(book);
    setEditForm({
      title: book.title,
      author_name: book.author_name,
      category: book.category,
      price: book.price || 0
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
      
      await axios.put(`${API}/books/${editingBook.id}`, formData, { withCredentials: true });
      
      setBooks(books.map(b => b.id === editingBook.id ? { ...b, ...editForm } : b));
      closeEditModal();
      alert("Publicación actualizada con éxito");
    } catch (error) {
      alert("Error al actualizar la publicación.");
      console.error(error);
    }
  };

  const totalWriters = usersList.filter(u => u.books_count > 0).length;
  const totalAdmins = usersList.filter(u => u.role === 'admin').length;
  const totalBanned = usersList.filter(u => u.is_banned).length;

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-24">
      <Navbar />
      <main className="max-w-6xl mx-auto px-6 pt-12">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white font-['Outfit']">
              {user?.role === 'admin' ? 'Panel de Administración' : 'Panel de Escritor'}
            </h1>
            <p className="text-sm text-[#A0A0A0] mt-1">
              {user?.role === 'admin' 
                ? 'Gestiona todo el catálogo de libros y los usuarios de la plataforma.' 
                : 'Gestiona tus publicaciones y sube nuevo contenido.'}
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            <Link to="/admin/new-book" className="flex items-center gap-2 bg-[#D92B2B] hover:bg-[#F03C3C] text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors">
              <Plus className="w-4 h-4" /> Nueva Publicación
            </Link>
            {user?.role === 'admin' && (
              <Link to="/admin/import" className="flex items-center gap-2 bg-[#121212] border border-white/10 hover:border-white/20 text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors shadow-lg">
                <FileArchive className="w-4 h-4" /> Importar ZIP Masivo
              </Link>
            )}
          </div>
        </div>

        {user?.role === 'admin' && (
          <div className="flex gap-4 border-b border-white/10 mb-8">
            <button 
              onClick={() => setActiveTab('books')}
              className={`pb-3 px-2 text-sm font-semibold transition-colors border-b-2 ${activeTab === 'books' ? 'border-[#D92B2B] text-white' : 'border-transparent text-[#A0A0A0] hover:text-[#F5F5F5]'}`}
            >
              Publicaciones
            </button>
            <button 
              onClick={() => setActiveTab('users')}
              className={`pb-3 px-2 text-sm font-semibold transition-colors border-b-2 ${activeTab === 'users' ? 'border-[#D92B2B] text-white' : 'border-transparent text-[#A0A0A0] hover:text-[#F5F5F5]'}`}
            >
              Gestión de Usuarios
            </button>
          </div>
        )}

        {loading ? (
          <div className="text-center text-[#A0A0A0] py-20">Cargando datos...</div>
        ) : activeTab === 'books' ? (
          /* PESTAÑA LIBROS */
          books.length === 0 ? (
            <div className="bg-[#121212] border border-white/5 rounded-xl p-12 text-center">
              <p className="text-[#A0A0A0] mb-4">No hay publicaciones aún.</p>
              <Link to="/admin/new-book" className="text-[#D92B2B] hover:underline font-semibold">Comienza a publicar ahora</Link>
            </div>
          ) : (
            <div className="bg-[#121212] border border-white/10 rounded-xl overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse min-w-[800px]">
                  <thead>
                    <tr className="bg-[#1A1A1A] border-b border-white/10 text-[#A0A0A0] text-xs uppercase tracking-wider">
                      <th className="p-4 font-semibold">Título y Portada</th>
                      <th className="p-4 font-semibold">Autor</th>
                      <th className="p-4 font-semibold">Categoría</th>
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
                        <td className="p-4 text-[#A0A0A0] text-sm">
                          <span className="bg-[#D92B2B]/10 text-[#D92B2B] px-2 py-1 rounded text-xs font-semibold uppercase">{book.category}</span>
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
        ) : (
          /* PESTAÑA USUARIOS */
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
                  <span className="text-sm font-semibold uppercase tracking-wider">Total Escritores</span>
                </div>
                <div className="text-3xl font-bold text-white">{totalWriters}</div>
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
                          {u.role === 'admin' 
                            ? <span className="bg-[#D4AF37]/10 text-[#D4AF37] px-2 py-1 rounded text-xs font-semibold uppercase border border-[#D4AF37]/20">Admin</span>
                            : <span className="bg-white/5 text-[#A0A0A0] px-2 py-1 rounded text-xs font-semibold uppercase border border-white/10">User</span>
                          }
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
                                ? 'bg-transparent text-[#404040] border-[#303030] cursor-not-allowed'
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
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Precio</label>
                <input type="number" step="0.01" value={editForm.price} onChange={(e) => setEditForm({...editForm, price: e.target.value})} className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-2.5 text-[#F5F5F5] focus:border-[#D92B2B] focus:outline-none" />
              </div>
              <div className="pt-4 flex gap-3">
                <button type="button" onClick={closeEditModal} className="flex-1 bg-white/5 hover:bg-white/10 text-white font-semibold py-3 rounded-lg transition-colors">Cancelar</button>
                <button type="submit" className="flex-1 bg-[#D92B2B] hover:bg-[#F03C3C] text-white font-semibold py-3 rounded-lg transition-colors">Guardar Cambios</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
