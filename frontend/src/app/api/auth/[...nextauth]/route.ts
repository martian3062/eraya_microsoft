import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import CredentialsProvider from "next-auth/providers/credentials";

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const handler = NextAuth({
  providers: [
    /* ── Google OAuth ───────────────────────────────────────────── */
    GoogleProvider({
      clientId:     process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),

    /* ── Email / password via Django SQLite ─────────────────────── */
    CredentialsProvider({
      id: "credentials",
      name: "Email",
      credentials: {
        email:    { label: "Email",    type: "email"    },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;
        try {
          const res = await fetch(`${BACKEND}/api/eraya-auth/login/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email:    credentials.email,
              password: credentials.password,
            }),
          });
          if (!res.ok) return null;
          const user = await res.json() as { id: string; email: string; name: string };
          return { id: user.id, email: user.email, name: user.name };
        } catch {
          return null;
        }
      },
    }),
  ],

  pages: {
    signIn: "/",
    error:  "/",
  },

  session: { strategy: "jwt" },

  callbacks: {
    async redirect() {
      return "/dashboard";
    },
    async jwt({ token, user }) {
      if (user) {
        token.id   = user.id;
        token.name = user.name;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as { id?: string }).id = token.id as string;
      }
      return session;
    },
  },

  secret: process.env.NEXTAUTH_SECRET,
});

export { handler as GET, handler as POST };
