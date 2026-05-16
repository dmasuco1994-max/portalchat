import Link from "next/link";
import { MessageSquare, Shield, Zap } from "lucide-react";

import { Brand } from "@/components/app/brand";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main className="grid min-h-screen lg:grid-cols-[1fr_minmax(420px,540px)]">
      {/* Left: brand + value props (hidden on mobile) */}
      <aside className="relative hidden overflow-hidden bg-brand-gradient lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div className="absolute inset-0 opacity-30 mix-blend-overlay">
          <div className="absolute -left-20 -top-20 size-[420px] rounded-full bg-white/30 blur-3xl" />
          <div className="absolute -bottom-32 -right-10 size-[480px] rounded-full bg-white/20 blur-3xl" />
        </div>

        <Link href="/" className="relative z-10 inline-block">
          <Brand size="lg" inverse />
        </Link>

        <div className="relative z-10 space-y-10 text-white">
          <div>
            <h1 className="text-3xl font-semibold leading-tight tracking-tight md:text-4xl">
              Tu WhatsApp Business,
              <br />
              <span className="text-white/85">enchufado a tu CRM.</span>
            </h1>
            <p className="mt-4 max-w-md text-base text-white/80">
              Conectá varios números, enrutá conversaciones a tu equipo, y
              hacé seguimiento real desde una plataforma sola.
            </p>
          </div>

          <ul className="grid gap-5">
            <ValueProp
              icon={<MessageSquare className="size-5" />}
              title="Multi-número, multi-equipo"
              body="Manejá cuantos números necesites desde una sola cuenta, con permisos por rol."
            />
            <ValueProp
              icon={<Zap className="size-5" />}
              title="Integración nativa con tu CRM"
              body="Webhooks bidireccionales, formato apiwha, Neotel External y custom JSON firmado."
            />
            <ValueProp
              icon={<Shield className="size-5" />}
              title="Tokens efímeros, secrets en memoria"
              body="Auth con refresh rotation y cookies httpOnly. Nada de tokens persistidos en el browser."
            />
          </ul>
        </div>

        <p className="relative z-10 text-xs text-white/60">
          © {new Date().getFullYear()} Portal.chat · Comunicación profesional
          sobre WhatsApp
        </p>
      </aside>

      {/* Right: form area */}
      <section className="flex flex-col bg-background">
        <header className="flex items-center justify-between px-6 py-5 lg:hidden">
          <Brand size="md" />
        </header>
        <div className="flex flex-1 items-center justify-center px-6 py-12 lg:px-12">
          <div className="w-full max-w-sm">{children}</div>
        </div>
      </section>
    </main>
  );
}

function ValueProp({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <li className="flex items-start gap-4">
      <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-white/15 text-white backdrop-blur">
        {icon}
      </span>
      <div>
        <p className="font-medium text-white">{title}</p>
        <p className="mt-0.5 text-sm text-white/75">{body}</p>
      </div>
    </li>
  );
}
