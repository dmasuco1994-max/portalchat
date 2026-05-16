"use client";

import { Key, Mail, User } from "lucide-react";

import { useAuth } from "@/components/providers/auth-provider";
import { PageHeader } from "@/components/app/page-header";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function SettingsPage() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ajustes"
        description="Tu perfil, accesos y workspace."
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="size-4 text-primary" />
            Perfil
          </CardTitle>
          <CardDescription>Datos que ven tus compañeros de equipo.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm sm:grid-cols-2">
          <Field label="Nombre" value={user.full_name} />
          <Field label="Email" value={user.email} />
          <Field label="Rol" value={user.role} />
          <Field label="Estado" value={user.is_active ? "Activo" : "Inactivo"} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="size-4 text-primary" />
            Contraseña
          </CardTitle>
          <CardDescription>
            El cambio de contraseña self-service llega en la siguiente release.
            Por ahora, pedile al owner del workspace que rote la tuya si lo
            necesitás urgente.
          </CardDescription>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="size-4 text-primary" />
            Notificaciones
          </CardTitle>
          <CardDescription>
            Próximamente: alertas por mail cuando un número se desconecta,
            cuando una entrega de webhook falla repetidamente, o cuando el
            volumen de mensajes pasa un umbral.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-0.5 font-medium">{value}</p>
    </div>
  );
}
