import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { DollarSign, ShoppingBag, Users, TrendingUp } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || '/api';

export default function SellerDashboardPage() {
  const [sales, setSales] = useState([]);
  const [stats, setStats] = useState({ total_sales: 0, total_revenue: 0, unique_buyers: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSales();
  }, []);

  const loadSales = async () => {
    try {
      const { data } = await axios.get(`${API}/seller/sales`);
      setSales(data.sales);
      setStats(data.stats);
    } catch (err) {
      console.error('Error cargando ventas:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] pt-24 pb-20 px-4">
        <div className="text-center text-[#A0A0A0]">Cargando...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A] pt-24 pb-20 px-4">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-white mb-8">Panel de Ventas</h1>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="ae-card p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-[#D92B2B]/10 flex items-center justify-center">
                <ShoppingBag className="w-6 h-6 text-[#D92B2B]" />
              </div>
              <div>
                <p className="text-[#A0A0A0] text-sm">Total Ventas</p>
                <p className="text-2xl font-bold text-white">{stats.total_sales}</p>
              </div>
            </div>
          </div>

          <div className="ae-card p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-green-500/10 flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-green-400" />
              </div>
              <div>
                <p className="text-[#A0A0A0] text-sm">Ingresos Totales</p>
                <p className="text-2xl font-bold text-white">S/ {stats.total_revenue.toFixed(2)}</p>
              </div>
            </div>
          </div>

          <div className="ae-card p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <Users className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <p className="text-[#A0A0A0] text-sm">Clientes Únicos</p>
                <p className="text-2xl font-bold text-white">{stats.unique_buyers}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Sales Table */}
        <div className="ae-card p-6">
          <h2 className="text-xl font-bold text-white mb-6">Historial de Ventas</h2>
          
          {sales.length === 0 ? (
            <div className="text-center py-12 text-[#A0A0A0]">
              Aún no tienes ventas. ¡Publica tus libros para comenzar!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left py-3 px-4 text-[#A0A0A0] text-sm font-semibold">Orden</th>
                    <th className="text-left py-3 px-4 text-[#A0A0A0] text-sm font-semibold">Libro</th>
                    <th className="text-left py-3 px-4 text-[#A0A0A0] text-sm font-semibold">Comprador</th>
                    <th className="text-left py-3 px-4 text-[#A0A0A0] text-sm font-semibold">Tipo</th>
                    <th className="text-left py-3 px-4 text-[#A0A0A0] text-sm font-semibold">Monto</th>
                    <th className="text-left py-3 px-4 text-[#A0A0A0] text-sm font-semibold">Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {sales.map((sale) => (
                    <tr key={sale.id} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-3 px-4 text-white text-sm">{sale.order_number}</td>
                      <td className="py-3 px-4 text-white text-sm">{sale.book_title}</td>
                      <td className="py-3 px-4 text-[#A0A0A0] text-sm">{sale.buyer_name}</td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-1 rounded text-xs bg-[#D92B2B]/10 text-[#D92B2B]">
                          {sale.order_type === 'digital_purchase' ? 'Digital' : 
                           sale.order_type === 'digital_rental' ? 'Alquiler' : 'Físico'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-white text-sm font-semibold">
                        {sale.currency} {parseFloat(sale.total).toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-[#A0A0A0] text-sm">
                        {new Date(sale.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
