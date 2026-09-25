import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth, ROLE_HOME, ROLE_LABEL } from "../context/AuthContext";
import { api } from "../lib/api";
import { Bell, LogOut, Home } from "lucide-react";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuTrigger, DropdownMenuLabel, DropdownMenuSeparator,
} from "./ui/dropdown-menu";
import { Button } from "./ui/button";

export function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [notifs, setNotifs] = useState([]);

  useEffect(() => {
    if (!user) return;
    const load = () => api.get("/notifications").then((r) => setNotifs(r.data)).catch(() => {});
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [user]);

  const unread = notifs.filter((n) => !n.read).length;

  const markRead = async (id) => {
    await api.post(`/notifications/${id}/read`).catch(() => {});
    setNotifs((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  };

  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/85 border-b border-slate-200/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <Link to="/" data-testid="nav-logo" className="flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-lg bg-[hsl(var(--primary))] grid place-items-center">
            <Home className="h-5 w-5 text-white" />
          </div>
          <div className="leading-tight">
            <p className="font-heading font-bold text-slate-800">Rumah KORPRI</p>
            <p className="text-[10px] text-slate-500 -mt-0.5">Pemesanan & CRM KPR</p>
          </div>
        </Link>

        <div className="flex items-center gap-2">
          <Link to="/arsitektur" className="hidden sm:block text-sm text-slate-600 hover:text-[hsl(var(--primary))] px-3">
            Dokumentasi
          </Link>
          {!user ? (
            <>
              <Button variant="ghost" data-testid="nav-login-btn" onClick={() => navigate("/login")}>Masuk</Button>
              <Button data-testid="nav-register-btn" className="bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90" onClick={() => navigate("/login?mode=register")}>
                Daftar
              </Button>
            </>
          ) : (
            <>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button data-testid="nav-notif-btn" className="relative h-10 w-10 grid place-items-center rounded-lg hover:bg-slate-100">
                    <Bell className="h-5 w-5 text-slate-600" />
                    {unread > 0 && (
                      <span className="absolute top-1.5 right-1.5 h-4 min-w-4 px-1 rounded-full bg-[hsl(var(--accent))] text-white text-[10px] grid place-items-center">
                        {unread}
                      </span>
                    )}
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-80">
                  <DropdownMenuLabel>Notifikasi</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {notifs.length === 0 && <div className="px-2 py-4 text-sm text-slate-400 text-center">Belum ada notifikasi</div>}
                  {notifs.slice(0, 8).map((n) => (
                    <button key={n.id} onClick={() => markRead(n.id)}
                      className={`w-full text-left px-3 py-2 rounded-md hover:bg-slate-50 ${!n.read ? "bg-[hsl(var(--secondary))]/40" : ""}`}>
                      <p className="text-sm font-medium text-slate-800">{n.title}</p>
                      <p className="text-xs text-slate-500 line-clamp-2">{n.message}</p>
                    </button>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button data-testid="nav-user-btn" className="flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-lg hover:bg-slate-100">
                    <div className="h-8 w-8 rounded-full bg-[hsl(var(--primary))] text-white grid place-items-center text-sm font-semibold">
                      {user.name?.[0]}
                    </div>
                    <div className="hidden sm:block text-left leading-tight">
                      <p className="text-sm font-medium text-slate-800">{user.name?.split(" ")[0]}</p>
                      <p className="text-[10px] text-slate-500">{ROLE_LABEL[user.role]}</p>
                    </div>
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => navigate(ROLE_HOME[user.role])} data-testid="nav-dashboard-link">
                    Dashboard Saya
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => { logout(); navigate("/"); }} data-testid="nav-logout-btn" className="text-red-600">
                    <LogOut className="h-4 w-4 mr-2" /> Keluar
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
