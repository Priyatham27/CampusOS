"use client";

import React, { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { Palette, Globe, Layers, Check } from "lucide-react";

// Branding update validation schema
const settingsSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  primary_color: z.string().regex(/^#[0-9a-fA-F]{6}$/, "Must be a valid hex color (e.g. #4f46e5)"),
  secondary_color: z.string().regex(/^#[0-9a-fA-F]{6}$/, "Must be a valid hex color (e.g. #0891b2)"),
  custom_domain: z.string().optional().or(z.literal("")),
});

type SettingsFormValues = z.infer<typeof settingsSchema>;

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { success, error: toastError } = useToast();

  const tenant = user?.tenant;

  // Setup form
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<SettingsFormValues>({
    resolver: zodResolver(settingsSchema),
  });

  // Populate form with current tenant data when loaded
  useEffect(() => {
    if (tenant) {
      reset({
        name: tenant.name,
        primary_color: tenant.config.theme.primary_color || "#4f46e5",
        secondary_color: tenant.config.theme.secondary_color || "#0891b2",
        custom_domain: tenant.config.custom_domain || "",
      });
    }
  }, [tenant, reset]);

  const watchedPrimary = watch("primary_color") || "#4f46e5";
  const watchedSecondary = watch("secondary_color") || "#0891b2";
  const watchedName = watch("name") || "Institution";

  // Update Settings Mutation
  const updateSettingsMutation = useMutation({
    mutationFn: (data: SettingsFormValues) => {
      if (!tenant?.id) throw new Error("No Tenant ID found");
      return api.put(`/organizations/${tenant.id}`, {
        name: data.name,
        config: {
          theme: {
            primary_color: data.primary_color,
            secondary_color: data.secondary_color,
          },
          custom_domain: data.custom_domain || null,
        },
      });
    },
    onSuccess: async () => {
      // Invalidate current user to trigger reloading dynamic color themes globally!
      await queryClient.invalidateQueries({ queryKey: ["current_user"] });
      success("Branding Configured", "White-labeled branding settings updated.");
    },
    onError: (err: any) => {
      toastError("Update Failed", err?.detail || "An error occurred.");
    },
  });

  const onSubmit = (data: SettingsFormValues) => {
    updateSettingsMutation.mutate(data);
  };

  // Color preset buttons
  const themePresets = [
    { primary: "#4f46e5", secondary: "#0891b2", name: "Royal Purple" },
    { primary: "#0ea5e9", secondary: "#10b981", name: "Tech Ocean" },
    { primary: "#10b981", secondary: "#f59e0b", name: "Eco Gold" },
    { primary: "#e11d48", secondary: "#4f46e5", name: "Rose Indigo" },
  ];

  const handleApplyPreset = (p: typeof themePresets[0]) => {
    setValue("primary_color", p.primary, { shouldValidate: true });
    setValue("secondary_color", p.secondary, { shouldValidate: true });
  };

  // Helper check for settings write permissions
  const canWriteSettings = user?.role?.permissions.includes("*") || user?.role?.permissions.includes("settings:write");

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight">White-Label Branding Controls</h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          Configure branding properties, theme color definitions, and domain settings for your institution.
        </p>
      </div>

      {/* Main Layout split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Settings Form */}
        <Card glass className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Branding Configurations</CardTitle>
            <CardDescription>
              Provide your college name, logo guidelines, and default HSL hex colors.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5">
              <Input
                type="text"
                label="Institution Name"
                placeholder="State University"
                disabled={!canWriteSettings}
                error={errors.name?.message}
                {...register("name")}
              />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  type="text"
                  label="Primary Accent Hex"
                  placeholder="#4f46e5"
                  disabled={!canWriteSettings}
                  error={errors.primary_color?.message}
                  {...register("primary_color")}
                />

                <Input
                  type="text"
                  label="Secondary Accent Hex"
                  placeholder="#0891b2"
                  disabled={!canWriteSettings}
                  error={errors.secondary_color?.message}
                  {...register("secondary_color")}
                />
              </div>

              {/* Theme presets picker helper */}
              {canWriteSettings && (
                <div className="flex flex-col gap-2">
                  <span className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Color Presets
                  </span>
                  <div className="flex flex-wrap gap-2.5">
                    {themePresets.map((p) => {
                      const isActive = watchedPrimary === p.primary && watchedSecondary === p.secondary;
                      return (
                        <button
                          key={p.name}
                          type="button"
                          onClick={() => handleApplyPreset(p)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs hover:bg-accent/10 transition-colors cursor-pointer"
                        >
                          <span
                            className="h-3.5 w-3.5 rounded-full inline-block border border-white/10"
                            style={{ backgroundColor: p.primary }}
                          />
                          {p.name}
                          {isActive && <Check className="h-3 w-3 text-primary ml-1" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              <Input
                type="text"
                label="Custom DNS Domain (Optional)"
                placeholder="academy.institution.edu"
                disabled={!canWriteSettings}
                error={errors.custom_domain?.message}
                {...register("custom_domain")}
              />

              {canWriteSettings && (
                <div className="flex justify-end border-t border-border pt-4 mt-2">
                  <Button type="submit" isLoading={updateSettingsMutation.isPending}>
                    Save Branding Configurations
                  </Button>
                </div>
              )}
            </form>
          </CardContent>
        </Card>

        {/* Live Mock Visualizer Widget */}
        <div className="flex flex-col gap-6">
          <Card glass>
            <CardHeader>
              <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                Dynamic Theme Preview
              </CardTitle>
              <CardDescription>
                How components will render under active branding variables.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              {/* Mock Header element */}
              <div className="border border-border rounded-lg p-4 bg-background flex items-center justify-between shadow-md">
                <div className="flex items-center gap-2">
                  <div
                    className="h-7 w-7 rounded-lg flex items-center justify-center text-white text-xs font-bold"
                    style={{ backgroundColor: watchedPrimary }}
                  >
                    C
                  </div>
                  <span className="font-semibold text-xs truncate max-w-[120px]">{watchedName}</span>
                </div>
                <div
                  className="h-1.5 w-6 rounded-full"
                  style={{ backgroundColor: watchedSecondary }}
                />
              </div>

              {/* Mock dashboard card */}
              <div className="border border-border rounded-lg p-4 bg-background space-y-3 shadow-md">
                <div className="flex justify-between items-center">
                  <span className="text-3xs font-semibold text-muted-foreground uppercase">Metrics log</span>
                  <div
                    className="h-3.5 w-3.5 rounded-full border flex items-center justify-center text-white"
                    style={{ backgroundColor: watchedPrimary, borderColor: watchedPrimary }}
                  >
                    <Check className="h-2 w-2" />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <div className="h-3.5 w-16 bg-muted rounded animate-pulse" />
                  <div className="h-3 w-full bg-muted rounded animate-pulse" />
                </div>
              </div>

              <div className="text-3xs leading-relaxed text-muted-foreground text-center">
                Pressing Save updates the Organization Branding properties in MongoDB, pushing variables to active CSS properties.
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
