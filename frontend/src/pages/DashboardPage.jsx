import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { Pencil, Trash2, Plus, FileArchive, X } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function DashboardPage() {
  const { user } = useAuth();
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Modal Edit state
  const [editingBook, setEditingBook] = useState(null);
  const [editForm, setEditForm] = useState({ title: '', author_name: '', category: '', price: 0 });

  useEffect(() => {
    fetchMyBooks();
  }, []);

  const fetchMyBooks = async () => {
    try {
      const endpoint = user?.role === 'admin' ? `${API}/books` : `${API}/users/me/books`;
      const { data } = await axios.get(endpoint, { withCredentials: true });
      setBooks(data);
    } catch (error) {
      console.error('Error fetching books:', error);
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
      
      // Update local state
      setBooks(books.map(b => b.id === editingBook.id ? { ...b, ...editForm } : b));
      closeEditModal();
      alert("Publicación actualizada con éxito");
    } catch (error) {
      alert("Error al actualizar la publicación.");
      console.error(error);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-24">
      <Navbar />
      <main className="max-w-6xl mx-auto px-6 pt-12">
        <div className="flex flex-col md:flex-row items-center justify-between mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white font-['Outfit']">
              {user?.role === 'admin' ? 'Panel de Administración' : 'Panel de Escritor'}
            </h1>
            <p className="text-sm text-[#A0A0A0] mt-1">
              {user?.role === 'admin' 
                ? 'Gestiona todo el catálogo de libros de la plataforma.' 
                : 'Gestiona tus publicaciones y sube nuevo contenido.'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/admin/new-book" className="flex items-center gap-2 bg-[#D92B2B] hover:bg-[#F03C3C] text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors">
              <Plus className="w-4 h-4" /> Nueva Publicación
            </Link>
            {user?.role === 'admin' && (
              <Link to="/admin/import" className="flex items-center gap-2 bg-[#121212] border border-white/10 hover:border-white/20 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors">
                <FileArchive className="w-4 h-4" /> Importar ZIP (Admin)
              </Link>
            )}
          </div>
        </div>

        {loading ? (
          <div className="text-center text-[#A0A0A0] py-20">Cargando tus publicaciones...</div>
        ) : books.length === 0 ? (
          <div className="bg-[#121212] border border-white/5 rounded-xl p-12 text-center">
            <p className="text-[#A0A0A0] mb-4">No tienes publicaciones aún.</p>
            <Link to="/admin/new-book" className="text-[#D92B2B] hover:underline font-semibold">Comienza a publicar ahora</Link>
          </div>
        ) : (
          <div className="bg-[#121212] border border-white/10 rounded-xl overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#1A1A1A] border-b border-white/10 text-[#A0A0A0] text-xs uppercase tracking-wider">
                  <th className="p-4 font-semibold">Título</th>
                  <th className="p-4 font-semibold">Autor</th>
                  <th className="p-4 font-semibold">Categoría</th>
                  <th className="p-4 font-semibold text-center">Vistas / Likes</th>
                  <th className="p-4 font-semibold text-right">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {books.map(book => (
                  <tr key={book.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                    <td className="p-4 text-white font-medium">
                      <div className="flex items-center gap-3">
                        <img src={book.cover_image_url || 'https://via.placeholder.com/50'} alt={book.title} className="w-10 h-12 object-cover rounded-sm border border-white/10" />
                        <span className="line-clamp-2">{book.title}</span>
                      </div>
                    </td>
                    <td className="p-4 text-[#A0A0A0] text-sm">{book.author_name}</td>
                    <td className="p-4 text-[#A0A0A0] text-sm">
                      <span className="bg-[#D92B2B]/10 text-[#D92B2B] px-2 py-1 rounded text-xs font-semibold uppercase">{book.category}</span>
                    </td>
                    <td className="p-4 text-[#A0A0A0] text-sm text-center">
                      {book.views} / {book.likes}
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex justify-end gap-2">
                        <button onClick={() => openEditModal(book)} className="p-2 text-[#A0A0A0] hover:text-[#D4AF37] hover:bg-[#D4AF37]/10 rounded-lg transition-colors" title="Editar">
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleDelete(book.id)} className="p-2 text-[#A0A0A0] hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors" title="Eliminar">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
