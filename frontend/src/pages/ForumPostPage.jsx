import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { API } from '../config/api';
import { useAuth } from '../contexts/AuthContext';
import { Navbar } from '../components/Navbar';
import {
  ThumbsUp,
  Bookmark,
  BookmarkCheck,
  UserPlus,
  UserMinus,
  Send,
  Trash2,
  Edit3,
  Flag,
  CheckCircle,
  MessageCircle,
  ArrowLeft,
  Clock,
  Shield,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  X,
  Loader2
} from 'lucide-react';

const REPORT_REASONS = [
  { value: 'spam', label: 'Spam' },
  { value: 'offensive', label: 'Contenido ofensivo' },
  { value: 'harassment', label: 'Acoso' },
  { value: 'inappropriate', label: 'Inapropiado' },
  { value: 'off_topic', label: 'Fuera de tema' },
  { value: 'other', label: 'Otro' }
];

export default function ForumPostPage() {
  const { postId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [post, setPost] = useState(null);
  const [replies, setReplies] = useState([]);
  const [repliesMeta, setRepliesMeta] = useState({ total: 0, page: 1, pages: 1 });
  const [loading, setLoading] = useState(true);
  const [liked, setLiked] = useState(false);
  const [bookmarked, setBookmarked] = useState(false);
  const [following, setFollowing] = useState(false);

  const [replyContent, setReplyContent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [editingReplyId, setEditingReplyId] = useState(null);
  const [editContent, setEditContent] = useState('');

  const [reportModal, setReportModal] = useState({ open: false, type: null, id: null });
  const [reportReason, setReportReason] = useState('');
  const [reportExplanation, setReportExplanation] = useState('');
  const [reportSubmitting, setReportSubmitting] = useState(false);

  const [deleteConfirm, setDeleteConfirm] = useState({ open: false, type: null, id: null });
  const [deleting, setDeleting] = useState(false);

  const fetchPost = useCallback(async () => {
    try {
      const res = await API.get(`/api/forum/posts/${postId}`);
      setPost(res.data.post);
      setLiked(res.data.user_liked);
      setBookmarked(res.data.user_bookmarked);
      setFollowing(res.data.user_following);
    } catch (err) {
      console.error('Error fetching post:', err);
    }
  }, [postId]);

  const fetchReplies = useCallback(async (page = 1) => {
    try {
      const res = await API.get(`/api/forum/posts/${postId}/replies`, {
        params: { page, limit: 10 }
      });
      setReplies(res.data.replies);
      setRepliesMeta({
        total: res.data.total,
        page: res.data.page,
        pages: res.data.pages
      });
    } catch (err) {
      console.error('Error fetching replies:', err);
    }
  }, [postId]);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([fetchPost(), fetchReplies()]);
      setLoading(false);
    };
    init();
  }, [fetchPost, fetchReplies]);

  const handleLike = async () => {
    try {
      const res = await API.post(`/api/forum/posts/${postId}/like`);
      setLiked(res.data.liked);
      setPost(prev => ({ ...prev, like_count: res.data.like_count }));
    } catch (err) {
      console.error('Error toggling like:', err);
    }
  };

  const handleBookmark = async () => {
    try {
      const res = await API.post(`/api/forum/posts/${postId}/bookmark`);
      setBookmarked(res.data.bookmarked);
    } catch (err) {
      console.error('Error toggling bookmark:', err);
    }
  };

  const handleFollow = async () => {
    try {
      const res = await API.post(`/api/forum/posts/${postId}/follow`);
      setFollowing(res.data.following);
    } catch (err) {
      console.error('Error toggling follow:', err);
    }
  };

  const handleReplySubmit = async (e) => {
    e.preventDefault();
    if (!replyContent.trim() || replyContent.length < 2) return;
    setSubmitting(true);
    try {
      await API.post(`/api/forum/posts/${postId}/replies`, { content: replyContent });
      setReplyContent('');
      await fetchReplies(repliesMeta.pages);
    } catch (err) {
      console.error('Error posting reply:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleAcceptReply = async (replyId) => {
    try {
      await API.post(`/api/forum/replies/${replyId}/accept`);
      await Promise.all([fetchPost(), fetchReplies(repliesMeta.page)]);
    } catch (err) {
      console.error('Error accepting reply:', err);
    }
  };

  const handleEditReply = async (replyId) => {
    if (!editContent.trim() || editContent.length < 2) return;
    try {
      await API.put(`/api/forum/replies/${replyId}`, { content: editContent });
      setEditingReplyId(null);
      setEditContent('');
      await fetchReplies(repliesMeta.page);
    } catch (err) {
      console.error('Error editing reply:', err);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm.type || !deleteConfirm.id) return;
    setDeleting(true);
    try {
      if (deleteConfirm.type === 'post') {
        await API.delete(`/api/forum/posts/${postId}`);
        navigate('/forum');
      } else {
        await API.delete(`/api/forum/replies/${deleteConfirm.id}`);
        await fetchReplies(repliesMeta.page);
        await fetchPost();
      }
      setDeleteConfirm({ open: false, type: null, id: null });
    } catch (err) {
      console.error('Error deleting:', err);
    } finally {
      setDeleting(false);
    }
  };

  const handleReportSubmit = async (e) => {
    e.preventDefault();
    if (!reportReason) return;
    setReportSubmitting(true);
    try {
      const payload = {
        reason: reportReason,
        explanation: reportExplanation
      };
      if (reportModal.type === 'post') {
        payload.post_id = reportModal.id;
      } else {
        payload.reply_id = reportModal.id;
      }
      await API.post('/api/forum/reports', payload);
      setReportModal({ open: false, type: null, id: null });
      setReportReason('');
      setReportExplanation('');
    } catch (err) {
      console.error('Error submitting report:', err);
    } finally {
      setReportSubmitting(false);
    }
  };

  const handleStatusChange = async (status) => {
    try {
      await API.put(`/api/admin/forum/posts/${postId}/status`, { status });
      await fetchPost();
    } catch (err) {
      console.error('Error changing status:', err);
    }
  };

  const formatDate = (dateStr) => {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now - d;
    const diffMin = Math.floor(diffMs / 60000);
    const diffHr = Math.floor(diffMs / 3600000);
    const diffDay = Math.floor(diffMs / 86400000);
    if (diffMin < 1) return 'Ahora mismo';
    if (diffMin < 60) return `hace ${diffMin} min`;
    if (diffHr < 24) return `hace ${diffHr}h`;
    if (diffDay < 30) return `hace ${diffDay}d`;
    return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex flex-col">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-[#D92B2B] animate-spin" />
        </div>
      </div>
    );
  }

  if (!post) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex flex-col">
        <Navbar />
        <div className="flex-1 flex flex-col items-center justify-center text-[#A0A0A0]">
          <AlertTriangle className="w-12 h-12 mb-4" />
          <p className="text-lg">Publicación no encontrada</p>
          <Link to="/forum" className="mt-4 text-[#D92B2B] hover:text-[#F03C3C] transition-colors">
            Volver al foro
          </Link>
        </div>
      </div>
    );
  }

  const isOwner = user && post.user_id === user.id;
  const isAdmin = user && user.role === 'admin';

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 py-8">
        <Link
          to="/forum"
          className="inline-flex items-center gap-2 text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Volver al foro
        </Link>

        {post.status === 'closed' && (
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 mb-6 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0" />
            <p className="text-yellow-200 text-sm">Esta publicación está cerrada. No se permiten nuevas respuestas.</p>
          </div>
        )}

        {post.status === 'hidden' && (
          <div className="bg-[#D92B2B]/10 border border-[#D92B2B]/30 rounded-lg p-4 mb-6 flex items-center gap-3">
            <Shield className="w-5 h-5 text-[#D92B2B] flex-shrink-0" />
            <p className="text-[#F03C3C] text-sm">Esta publicación ha sido ocultada por un administrador.</p>
          </div>
        )}

        <div className="bg-[#121212] border border-white/10 rounded-xl p-6 mb-6">
          <div className="flex items-start justify-between gap-4 mb-4">
            <h1 className="text-2xl font-bold text-[#F5F5F5] flex-1">{post.title}</h1>
            {(isOwner || isAdmin) && (
              <div className="flex items-center gap-2 flex-shrink-0">
                {isAdmin && (
                  <div className="relative group">
                    <button className="px-3 py-1.5 text-xs font-medium bg-[#1A1A1A] border border-white/10 rounded-lg text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors flex items-center gap-1">
                      <Shield className="w-3 h-3" />
                      Estado
                    </button>
                    <div className="absolute right-0 top-full mt-1 bg-[#1A1A1A] border border-white/10 rounded-lg shadow-xl z-20 hidden group-hover:block min-w-[140px]">
                      {['active', 'hidden', 'closed'].map(s => (
                        <button
                          key={s}
                          onClick={() => handleStatusChange(s)}
                          className={`block w-full text-left px-4 py-2 text-sm transition-colors first:rounded-t-lg last:rounded-b-lg ${
                            post.status === s
                              ? 'bg-white/10 text-[#F5F5F5]'
                              : 'text-[#A0A0A0] hover:bg-white/5 hover:text-[#F5F5F5]'
                          }`}
                        >
                          {s === 'active' ? 'Activo' : s === 'hidden' ? 'Oculto' : 'Cerrado'}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                <button
                  onClick={() => setDeleteConfirm({ open: true, type: 'post', id: postId })}
                  className="p-2 text-[#606060] hover:text-[#D92B2B] hover:bg-[#D92B2B]/10 rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

          <div className="flex items-center gap-3 mb-4 text-sm">
            <span className="text-[#D4AF37] font-medium">{post.username}</span>
            <span className="text-[#606060]">·</span>
            <span className="text-[#606060] flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatDate(post.created_at)}
            </span>
            {post.category_name && (
              <>
                <span className="text-[#606060]">·</span>
                <span className="px-2 py-0.5 bg-[#D92B2B]/10 text-[#D92B2B] text-xs rounded-full">
                  {post.category_name}
                </span>
              </>
            )}
            {post.book_title && (
              <>
                <span className="text-[#606060]">·</span>
                <span className="px-2 py-0.5 bg-[#D4AF37]/10 text-[#D4AF37] text-xs rounded-full">
                  {post.book_title}
                </span>
              </>
            )}
          </div>

          <div className="text-[#A0A0A0] leading-relaxed whitespace-pre-wrap mb-6">
            {post.content}
          </div>

          <div className="flex items-center gap-2 pt-4 border-t border-white/5">
            <button
              onClick={handleLike}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                liked
                  ? 'bg-[#D92B2B]/10 text-[#D92B2B]'
                  : 'text-[#606060] hover:text-[#F5F5F5] hover:bg-white/5'
              }`}
            >
              <ThumbsUp className={`w-4 h-4 ${liked ? 'fill-current' : ''}`} />
              <span>{post.like_count || 0}</span>
            </button>

            <button
              onClick={handleBookmark}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                bookmarked
                  ? 'bg-[#D4AF37]/10 text-[#D4AF37]'
                  : 'text-[#606060] hover:text-[#F5F5F5] hover:bg-white/5'
              }`}
            >
              {bookmarked ? <BookmarkCheck className="w-4 h-4" /> : <Bookmark className="w-4 h-4" />}
            </button>

            {!isOwner && user && (
              <button
                onClick={handleFollow}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  following
                    ? 'bg-blue-500/10 text-blue-400'
                    : 'text-[#606060] hover:text-[#F5F5F5] hover:bg-white/5'
                }`}
              >
                {following ? <UserMinus className="w-4 h-4" /> : <UserPlus className="w-4 h-4" />}
                <span>{following ? 'Siguiendo' : 'Seguir'}</span>
              </button>
            )}

            <div className="flex items-center gap-2 text-[#606060] text-sm ml-auto">
              <MessageCircle className="w-4 h-4" />
              <span>{repliesMeta.total} respuestas</span>
            </div>

            {user && !isOwner && (
              <button
                onClick={() => setReportModal({ open: true, type: 'post', id: postId })}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-[#606060] hover:text-[#F03C3C] hover:bg-[#D92B2B]/10 transition-colors"
              >
                <Flag className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        <div className="mb-6">
          <h2 className="text-lg font-semibold text-[#F5F5F5] mb-4">
            Respuestas ({repliesMeta.total})
          </h2>

          <div className="space-y-4">
            {replies.map(reply => (
              <div
                key={reply.id}
                className={`bg-[#121212] border rounded-xl p-5 ${
                  reply.accepted
                    ? 'border-emerald-500/30 bg-emerald-500/5'
                    : 'border-white/10'
                }`}
              >
                {reply.accepted && (
                  <div className="flex items-center gap-2 mb-3 text-emerald-400 text-sm font-medium">
                    <CheckCircle className="w-4 h-4" />
                    Solución aceptada
                  </div>
                )}

                <div className="flex items-center justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-[#D4AF37] font-medium text-sm">{reply.username}</span>
                    <span className="text-[#606060] text-xs">{formatDate(reply.created_at)}</span>
                    {reply.updated_at !== reply.created_at && (
                      <span className="text-[#606060] text-xs italic">(editado)</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    {isOwner && !reply.accepted && post.status !== 'closed' && (
                      <button
                        onClick={() => handleAcceptReply(reply.id)}
                        className="p-1.5 text-[#606060] hover:text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors"
                        title="Aceptar como solución"
                      >
                        <CheckCircle className="w-4 h-4" />
                      </button>
                    )}
                    {user && user.id === reply.user_id && post.status !== 'closed' && (
                      <button
                        onClick={() => {
                          setEditingReplyId(reply.id);
                          setEditContent(reply.content);
                        }}
                        className="p-1.5 text-[#606060] hover:text-[#D4AF37] hover:bg-[#D4AF37]/10 rounded-lg transition-colors"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                    )}
                    {(user?.id === reply.user_id || isAdmin) && (
                      <button
                        onClick={() => setDeleteConfirm({ open: true, type: 'reply', id: reply.id })}
                        className="p-1.5 text-[#606060] hover:text-[#D92B2B] hover:bg-[#D92B2B]/10 rounded-lg transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                    {user && user.id !== reply.user_id && (
                      <button
                        onClick={() => setReportModal({ open: true, type: 'reply', id: reply.id })}
                        className="p-1.5 text-[#606060] hover:text-[#F03C3C] hover:bg-[#D92B2B]/10 rounded-lg transition-colors"
                      >
                        <Flag className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>

                {editingReplyId === reply.id ? (
                  <div>
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg p-3 text-[#F5F5F5] text-sm resize-none focus:outline-none focus:border-[#D92B2B] transition-colors"
                      rows={4}
                    />
                    <div className="flex justify-end gap-2 mt-2">
                      <button
                        onClick={() => { setEditingReplyId(null); setEditContent(''); }}
                        className="px-3 py-1.5 text-sm text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors"
                      >
                        Cancelar
                      </button>
                      <button
                        onClick={() => handleEditReply(reply.id)}
                        disabled={!editContent.trim() || editContent.length < 2}
                        className="px-3 py-1.5 text-sm bg-[#D92B2B] text-white rounded-lg hover:bg-[#F03C3C] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Guardar
                      </button>
                    </div>
                  </div>
                ) : (
                  <p className="text-[#A0A0A0] text-sm leading-relaxed whitespace-pre-wrap">
                    {reply.content}
                  </p>
                )}
              </div>
            ))}
          </div>

          {repliesMeta.pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <button
                onClick={() => fetchReplies(repliesMeta.page - 1)}
                disabled={repliesMeta.page <= 1}
                className="p-2 text-[#606060] hover:text-[#F5F5F5] hover:bg-white/5 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              {Array.from({ length: repliesMeta.pages }, (_, i) => i + 1).map(p => (
                <button
                  key={p}
                  onClick={() => fetchReplies(p)}
                  className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                    p === repliesMeta.page
                      ? 'bg-[#D92B2B] text-white'
                      : 'text-[#606060] hover:text-[#F5F5F5] hover:bg-white/5'
                  }`}
                >
                  {p}
                </button>
              ))}
              <button
                onClick={() => fetchReplies(repliesMeta.page + 1)}
                disabled={repliesMeta.page >= repliesMeta.pages}
                className="p-2 text-[#606060] hover:text-[#F5F5F5] hover:bg-white/5 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          )}
        </div>

        {post.status !== 'closed' && user && (
          <div className="bg-[#121212] border border-white/10 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-[#F5F5F5] mb-3">Tu respuesta</h3>
            <form onSubmit={handleReplySubmit}>
              <textarea
                value={replyContent}
                onChange={(e) => setReplyContent(e.target.value)}
                placeholder="Escribe tu respuesta..."
                className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg p-3 text-[#F5F5F5] text-sm resize-none focus:outline-none focus:border-[#D92B2B] transition-colors min-h-[100px]"
                rows={4}
              />
              <div className="flex items-center justify-between mt-3">
                <span className={`text-xs ${replyContent.length < 2 ? 'text-[#606060]' : 'text-[#A0A0A0]'}`}>
                  {replyContent.length} caracteres
                </span>
                <button
                  type="submit"
                  disabled={submitting || !replyContent.trim() || replyContent.length < 2}
                  className="flex items-center gap-2 px-4 py-2 bg-[#D92B2B] text-white text-sm font-medium rounded-lg hover:bg-[#F03C3C] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                  Publicar
                </button>
              </div>
            </form>
          </div>
        )}

        {reportModal.open && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
            <div className="bg-[#121212] border border-white/10 rounded-xl p-6 w-full max-w-md">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-[#F5F5F5]">
                  Reportar {reportModal.type === 'post' ? 'publicación' : 'respuesta'}
                </h3>
                <button
                  onClick={() => { setReportModal({ open: false, type: null, id: null }); setReportReason(''); setReportExplanation(''); }}
                  className="p-1 text-[#606060] hover:text-[#F5F5F5] transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleReportSubmit}>
                <div className="space-y-2 mb-4">
                  {REPORT_REASONS.map(r => (
                    <label
                      key={r.value}
                      className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                        reportReason === r.value
                          ? 'border-[#D92B2B] bg-[#D92B2B]/10'
                          : 'border-white/10 hover:border-white/20'
                      }`}
                    >
                      <input
                        type="radio"
                        name="reason"
                        value={r.value}
                        checked={reportReason === r.value}
                        onChange={(e) => setReportReason(e.target.value)}
                        className="accent-[#D92B2B]"
                      />
                      <span className="text-sm text-[#F5F5F5]">{r.label}</span>
                    </label>
                  ))}
                </div>
                <textarea
                  value={reportExplanation}
                  onChange={(e) => setReportExplanation(e.target.value)}
                  placeholder="Explica el motivo (opcional)"
                  className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg p-3 text-[#F5F5F5] text-sm resize-none focus:outline-none focus:border-[#D92B2B] transition-colors mb-4"
                  rows={3}
                />
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => { setReportModal({ open: false, type: null, id: null }); setReportReason(''); setReportExplanation(''); }}
                    className="px-4 py-2 text-sm text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={!reportReason || reportSubmitting}
                    className="px-4 py-2 text-sm bg-[#D92B2B] text-white rounded-lg hover:bg-[#F03C3C] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {reportSubmitting ? 'Enviando...' : 'Reportar'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {deleteConfirm.open && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
            <div className="bg-[#121212] border border-white/10 rounded-xl p-6 w-full max-w-sm">
              <h3 className="text-lg font-semibold text-[#F5F5F5] mb-2">
                Eliminar {deleteConfirm.type === 'post' ? 'publicación' : 'respuesta'}
              </h3>
              <p className="text-[#A0A0A0] text-sm mb-6">
                ¿Estás seguro de que deseas eliminar esta {deleteConfirm.type === 'post' ? 'publicación' : 'respuesta'}? Esta acción no se puede deshacer.
              </p>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setDeleteConfirm({ open: false, type: null, id: null })}
                  className="px-4 py-2 text-sm text-[#A0A0A0] hover:text-[#F5F5F5] transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="px-4 py-2 text-sm bg-[#D92B2B] text-white rounded-lg hover:bg-[#F03C3C] transition-colors disabled:opacity-50"
                >
                  {deleting ? 'Eliminando...' : 'Eliminar'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
