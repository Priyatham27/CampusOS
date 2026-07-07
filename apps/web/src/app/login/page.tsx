"use client";

import React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { GraduationCap, ArrowRight, Sparkles } from "lucide-react";

// Form validation schema
const loginSchema = z.object({
  email: z.string().min(1, "Email is required").email("Invalid email address"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { login, isLoggingIn } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "admin@campusos.com",
      password: "password123",
    },
  });

  const onSubmit = (data: LoginFormValues) => {
    login(data);
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-[#07070a] overflow-hidden px-4">
      {/* Dynamic Background Gradients */}
      <div className="absolute top-[-20%] left-[-20%] w-[60%] h-[60%] rounded-full bg-primary/20 blur-[150px]" />
      <div className="absolute bottom-[-20%] right-[-20%] w-[60%] h-[60%] rounded-full bg-[#0891b2]/10 blur-[150px]" />

      {/* Login Container */}
      <div className="w-full max-w-md z-10 flex flex-col gap-6">
        {/* Branding header */}
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="h-12 w-12 rounded-2xl bg-primary/10 text-primary border border-primary/20 flex items-center justify-center shadow-lg shadow-primary/5">
            <GraduationCap className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white flex items-center justify-center gap-1.5">
              Sign in to CampusOS <Sparkles className="h-4 w-4 text-primary animate-pulse" />
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Enterprise white-labeled platform access shell.
            </p>
          </div>
        </div>

        {/* Form Card */}
        <div className="glass-card p-8 flex flex-col gap-6 shadow-2xl border border-white/5 bg-white/[0.02]">
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <Input
              type="email"
              label="Admin / User Email"
              placeholder="name@institution.edu"
              error={errors.email?.message}
              {...register("email")}
              className="bg-white/[0.02] border-white/10 text-white placeholder:text-slate-500"
            />

            <Input
              type="password"
              label="Password"
              placeholder="••••••••"
              error={errors.password?.message}
              {...register("password")}
              className="bg-white/[0.02] border-white/10 text-white placeholder:text-slate-500"
            />

            <Button
              type="submit"
              isLoading={isLoggingIn}
              className="w-full mt-2 font-semibold flex items-center justify-center gap-1.5"
            >
              Sign In <ArrowRight className="h-4 w-4" />
            </Button>
          </form>

          {/* Quick-start Seeding Hint */}
          <div className="p-3 bg-white/[0.02] border border-white/5 rounded-lg text-3xs leading-relaxed text-slate-400 text-center">
            <span className="font-semibold text-primary block mb-0.5 uppercase tracking-wider">MVP Seeding Warning</span>
            Logging in defaults to auto-generating mock organization settings and a SuperAdmin profile: <strong className="text-white">admin@campusos.com / password123</strong>.
          </div>
        </div>
      </div>
    </div>
  );
}
