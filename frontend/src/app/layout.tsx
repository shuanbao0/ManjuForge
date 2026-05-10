import "./globals.css";
import { I18nProvider } from "@/i18n";

// Note: the legacy EnvConfigChecker auto-popup was removed when the multi-user
// rewrite moved provider keys (DashScope, OSS, Kling, Vidu, OpenAI) to
// per-user credentials at /me/credentials. Admins can still edit instance-wide
// .env defaults from Settings → Environment Configuration if needed.

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <head>
        <title>ManjuForge Studio</title>
        <meta name="description" content="AI-Native Motion Comic Creation Platform" />
      </head>
      <body className="font-sans bg-background text-foreground antialiased">
        <I18nProvider>{children}</I18nProvider>
      </body>
    </html>
  );
}
