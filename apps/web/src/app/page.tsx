"use client";

import React, { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { GraduationCap, ArrowRight, Palette, Layers, Globe, Shield, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function LandingPage() {
  // Preset list for interactive branding live demo
  const presets = [
    { name: "Indigo Legacy", primary: "#4f46e5", bg: "bg-indigo-600" },
    { name: "Emerald Tech", primary: "#10b981", bg: "bg-emerald-500" },
    { name: "Oceanic Academy", primary: "#0ea5e9", bg: "bg-sky-500" },
    { name: "Crimson State", primary: "#e11d48", bg: "bg-rose-600" },
  ];

  const [activePrimary, setActivePrimary] = useState(presets[0].primary);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.15 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  };

  return (
    <div className="relative min-h-screen bg-[#07070a] text-slate-100 overflow-hidden flex flex-col font-sans">
      {/* Dynamic Glow Orbs */}
      <div
        className="absolute top-[-25%] left-[-15%] w-[60%] h-[60%] rounded-full blur-[160px] opacity-25 transition-colors duration-700"
        style={{ backgroundColor: activePrimary }}
      />
      <div className="absolute bottom-[-20%] right-[-15%] w-[50%] h-[50%] rounded-full bg-[#0891b2]/10 blur-[160px]" />

      {/* Header */}
      <header className="h-20 border-b border-white/5 glass sticky top-0 z-50 flex items-center justify-between px-6 md:px-12">
        <div className="flex items-center gap-2">
          <div
            className="h-9 w-9 rounded-xl flex items-center justify-center text-white transition-colors duration-500"
            style={{ backgroundColor: activePrimary }}
          >
            <GraduationCap className="h-5 w-5" />
          </div>
          <span className="font-bold text-lg tracking-wider text-white">CampusOS</span>
        </div>

        <Link href="/login">
          <Button variant="outline" size="sm" className="border-white/10 text-white hover:bg-white/5">
            Admin Console
          </Button>
        </Link>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col justify-center items-center px-6 py-20 text-center max-w-5xl mx-auto w-full z-10 gap-16">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="flex flex-col items-center gap-6"
        >
          {/* Tagline Badge */}
          <motion.div
            variants={itemVariants}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/5 bg-white/[0.02] text-xs text-slate-400"
          >
            <Sparkles className="h-3 w-3" style={{ color: activePrimary }} />
            White-labeled Multi-Tenant Platform for Colleges
          </motion.div>

          {/* Headline */}
          <motion.h1
            variants={itemVariants}
            className="text-4xl md:text-6xl font-extrabold tracking-tight text-white max-w-3xl leading-tight"
          >
            The Modern Operating System for{" "}
            <span className="transition-colors duration-500" style={{ color: activePrimary }}>
              Your Campus
            </span>
          </motion.h1>

          {/* Description */}
          <motion.p
            variants={itemVariants}
            className="text-sm md:text-base text-slate-400 max-w-xl leading-relaxed"
          >
            A scalable, white-label cloud foundation powering educational operations, user permissions, settings, and modular plugin overrides.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div variants={itemVariants} className="flex gap-4 mt-2">
            <Link href="/login">
              <Button
                style={{ backgroundColor: activePrimary }}
                className="font-bold shadow-lg text-white border-0 hover:brightness-110 flex items-center gap-1.5"
              >
                Launch Platform Shell <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </motion.div>
        </motion.div>

        {/* Live White-Label Customization Demo widget */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="w-full max-w-3xl glass p-8 rounded-2xl border border-white/5 bg-white/[0.01]"
        >
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="text-left flex flex-col gap-1.5 max-w-sm">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Palette className="h-4 w-4" style={{ color: activePrimary }} /> Live White-Label Presets
              </h3>
              <p className="text-2xs text-slate-400 leading-relaxed">
                Click presets to see the portal accent styling transition instantly. Every educational tenant controls its branding overrides.
              </p>
            </div>

            {/* Presets Grid */}
            <div className="flex flex-wrap gap-3">
              {presets.map((p) => (
                <button
                  key={p.name}
                  onClick={() => setActivePrimary(p.primary)}
                  className={`flex items-center gap-2 px-3.5 py-2.5 rounded-xl border text-xs font-semibold transition-all duration-300 hover:bg-white/5 cursor-pointer ${
                    activePrimary === p.primary
                      ? "border-white bg-white/5 text-white"
                      : "border-white/5 text-slate-400"
                  }`}
                >
                  <span className={`h-3 w-3 rounded-full ${p.bg} shadow-md`} />
                  {p.name}
                </button>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Core Capabilities Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full text-left mt-6">
          <div className="glass p-6 rounded-xl border border-white/5 bg-white/[0.01]">
            <div className="h-9 w-9 rounded-lg bg-white/5 flex items-center justify-center mb-4">
              <Globe className="h-4 w-4 text-slate-300" />
            </div>
            <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-1.5">Tenant Scoping</h4>
            <p className="text-2xs text-slate-400 leading-relaxed">
              Multi-tenant architecture isolating databases, branding elements, configurations, and document assets by colleges.
            </p>
          </div>

          <div className="glass p-6 rounded-xl border border-white/5 bg-white/[0.01]">
            <div className="h-9 w-9 rounded-lg bg-white/5 flex items-center justify-center mb-4">
              <Shield className="h-4 w-4 text-slate-300" />
            </div>
            <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-1.5">RBAC security</h4>
            <p className="text-2xs text-slate-400 leading-relaxed">
              Fine-grained access rights mapping permissions, admin overrides, custom security levels, and audit logs.
            </p>
          </div>

          <div className="glass p-6 rounded-xl border border-white/5 bg-white/[0.01]">
            <div className="h-9 w-9 rounded-lg bg-white/5 flex items-center justify-center mb-4">
              <Layers className="h-4 w-4 text-slate-300" />
            </div>
            <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-1.5">Feature toggles</h4>
            <p className="text-2xs text-slate-400 leading-relaxed">
              Dynamically activate modules (Events, Attendance, Clubs) per organization to match specific institutional needs.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-8 border-t border-white/5 text-center text-3xs text-slate-500">
        © 2026 CampusOS. Built for Enterprise Scale. All Rights Reserved.
      </footer>
    </div>
  );
}
