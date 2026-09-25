import React, { useState } from "react";
import { useNavigate, useLocation, useSearchParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { useAuth, ROLE_HOME } from "../context/AuthContext";
import { formatApiErrorDetail } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Home, ArrowLeft } from "lucide-react";

const DEMO = [
  { role: "Admin KORPRI", email: "pardz2006@gmail.com", pass: "korpri123" },
  { role: "Developer", email: "developer@rumahkorpri.com", pass: "developer123" },
  { role: "Bank BTN", email: "btn@rumahkorpri.com", pass: "btn123" },
  { role: "Peminat (ASN)", email: "consumer@rumahkorpri.com", pass: "consumer123" },
];

export default function Login() {
  const [params] = useSearchParams();
  const [mode, setMode] = useState(params.get("mode") === "register" ? "register" : "login");
  const [form, setForm] = useState({ name: "", email: "", password: "", phone: "", nik: "", instansi: "", monthly_income: "", city: "", province: "" });
  const [busy, setBusy] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const loc = useLocation();

  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      let user;
      if (mode === "login") {
        user = await login(form.email, form.password);
      } else {
        user = await register({ ...form, monthly_income: form.monthly_income ? Number(form.monthly_income) : null });
      }
      toast.success("Berhasil masuk");
      navigate(loc.state?.from || ROLE_HOME[user.role] || "/", { replace: true });
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setBusy(false);
    }
  };

  const quickFill = (d) => { setMode("login"); setForm({ ...form, email: d.email, password: d.pass }); };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="hidden lg:flex flex-col justify-between bg-[hsl(var(--primary))] p-12 grain relative">
        <Link to="/" className="relative flex items-center gap-2.5 text-white">
          <div className="h-9 w-9 rounded-lg bg-white/15 grid place-items-center"><Home className="h-5 w-5" /></div>
          <span className="font-heading font-bold text-lg">Rumah KORPRI</span>
        </Link>
        <div className="relative">
          <h2 className="font-heading text-3xl font-bold text-white leading-tight">Satu platform untuk seluruh perjalanan KPR ASN.</h2>
          <p className="text-white/75 mt-4">Peminat, Admin KORPRI, Developer, dan Bank BTN terhubung dalam satu alur kerja yang transparan.</p>
        </div>
        <div className="relative bg-white/10 rounded-xl p-4 backdrop-blur-md border border-white/15">
          <p className="text-white/90 text-sm font-medium mb-2">Akun Demo (klik untuk isi otomatis)</p>
          <div className="grid grid-cols-2 gap-2">
            {DEMO.map((d) => (
              <button key={d.email} onClick={() => quickFill(d)} data-testid={`demo-${d.role}`}
                className="text-left text-xs bg-white/10 hover:bg-white/20 rounded-lg px-3 py-2 text-white transition-colors">
                <p className="font-semibold">{d.role}</p>
                <p className="text-white/60 truncate">{d.email}</p>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-12 bg-[hsl(var(--background))]">
        <div className="w-full max-w-md">
          <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-[hsl(var(--primary))] mb-6">
            <ArrowLeft className="h-4 w-4" /> Kembali ke beranda
          </Link>
          <h1 className="font-heading text-3xl font-bold text-slate-800">{mode === "login" ? "Masuk Portal" : "Daftar sebagai Peminat"}</h1>
          <p className="text-slate-500 mt-1">{mode === "login" ? "Akses dashboard sesuai peran Anda." : "Buat akun untuk memesan unit rumah."}</p>

          <form onSubmit={submit} className="mt-8 space-y-4">
            {mode === "register" && (
              <>
                <Field label="Nama Lengkap" testid="reg-name"><Input value={form.name} onChange={upd("name")} required data-testid="input-name" /></Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="NIK / NIP"><Input value={form.nik} onChange={upd("nik")} data-testid="input-nik" /></Field>
                  <Field label="No. WhatsApp"><Input value={form.phone} onChange={upd("phone")} data-testid="input-phone" /></Field>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Instansi ASN"><Input value={form.instansi} onChange={upd("instansi")} data-testid="input-instansi" /></Field>
                  <Field label="Penghasilan/bln"><Input type="number" value={form.monthly_income} onChange={upd("monthly_income")} data-testid="input-income" /></Field>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Kota/Kab. Domisili"><Input value={form.city} onChange={upd("city")} data-testid="input-city" placeholder="mis. Bekasi" /></Field>
                  <Field label="Provinsi"><Input value={form.province} onChange={upd("province")} data-testid="input-province" placeholder="mis. Jawa Barat" /></Field>
                </div>
              </>
            )}
            <Field label="Email"><Input type="email" value={form.email} onChange={upd("email")} required data-testid="input-email" /></Field>
            <Field label="Kata Sandi"><Input type="password" value={form.password} onChange={upd("password")} required data-testid="input-password" /></Field>

            <Button type="submit" disabled={busy} data-testid="submit-auth-btn"
              className="w-full bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90">
              {busy ? "Memproses..." : mode === "login" ? "Masuk" : "Daftar"}
            </Button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-6">
            {mode === "login" ? "Belum punya akun? " : "Sudah punya akun? "}
            <button onClick={() => setMode(mode === "login" ? "register" : "login")}
              data-testid="toggle-mode-btn" className="text-[hsl(var(--primary))] font-medium hover:underline">
              {mode === "login" ? "Daftar sekarang" : "Masuk di sini"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-sm text-slate-600">{label}</Label>
      {children}
    </div>
  );
}
