"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useToast } from "@/components/ui/toast";
import { ShieldCheck, ShieldAlert, Plus, Trash2, Lock } from "lucide-react";
import { Role, Permission } from "@/types";

// Role create validation schema
const roleSchema = z.object({
  name: z.string().min(2, "Role name must be at least 2 characters"),
  description: z.string().optional(),
  permissions: z.array(z.string()).min(1, "Select at least one permission"),
});

type RoleFormValues = z.infer<typeof roleSchema>;

export default function RolesPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { success, error: toastError } = useToast();
  const [modalOpen, setModalOpen] = useState(false);

  // Fetch roles list
  const { data: roles = [], isLoading: rolesLoading } = useQuery<Role[]>({
    queryKey: ["roles_list"],
    queryFn: () => api.get<Role[]>("/roles"),
  });

  // Fetch system permissions list
  const { data: permissions = [], isLoading: permissionsLoading } = useQuery<Permission[]>({
    queryKey: ["permissions_list"],
    queryFn: () => api.get<Permission[]>("/roles/permissions/list"),
  });

  // Setup form resolver
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<RoleFormValues>({
    resolver: zodResolver(roleSchema),
    defaultValues: {
      permissions: [],
    },
  });

  const selectedPermissions = watch("permissions") || [];

  // Create Role Mutation
  const createRoleMutation = useMutation({
    mutationFn: (data: RoleFormValues) => {
      return api.post<Role>("/roles", data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["roles_list"] });
      success("Role Configured", "Access role has been created.");
      setModalOpen(false);
      reset();
    },
    onError: (err: any) => {
      toastError("Failed to Create Role", err?.detail || "An error occurred.");
    },
  });

  // Delete Role Mutation
  const deleteRoleMutation = useMutation({
    mutationFn: (roleId: string) => {
      return api.delete(`/roles/${roleId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["roles_list"] });
      success("Role Deleted", "Custom access profile removed.");
    },
    onError: (err: any) => {
      toastError("Failed to Delete Role", err?.detail || "An error occurred.");
    },
  });

  const onSubmit = (data: RoleFormValues) => {
    createRoleMutation.mutate(data);
  };

  const handleCheckboxChange = (name: string) => {
    const next = selectedPermissions.includes(name)
      ? selectedPermissions.filter((x) => x !== name)
      : [...selectedPermissions, name];
    setValue("permissions", next, { shouldValidate: true });
  };

  const handleDelete = (roleId: string) => {
    if (confirm("Are you sure you want to delete this role? It will verify that no users are currently assigned to it first.")) {
      deleteRoleMutation.mutate(roleId);
    }
  };

  // Helper check for role permissions
  const hasPermission = (permName: string) => {
    if (!user?.role?.permissions) return false;
    return user.role.permissions.includes("*") || user.role.permissions.includes(permName);
  };

  const isWritePermitted = hasPermission("roles:manage");

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Security & RBAC Profiles</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Create user roles, scope access levels, and assign granular system permissions.
          </p>
        </div>
        
        {isWritePermitted && (
          <Button onClick={() => setModalOpen(true)} className="flex items-center gap-2">
            <Plus className="h-4 w-4" /> Create Custom Role
          </Button>
        )}
      </div>

      {/* Roles Display Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {rolesLoading ? (
          <>
            <Skeleton className="h-36 w-full" />
            <Skeleton className="h-36 w-full" />
          </>
        ) : (
          roles.map((r) => (
            <Card key={r.id} glass className="relative flex flex-col justify-between">
              <div>
                <CardHeader className="flex flex-row items-start justify-between pb-2">
                  <div className="flex flex-col gap-1">
                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                      {r.name}
                      <span className={`text-4xs px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                        r.is_system ? "bg-primary/20 text-primary border border-primary/20" : "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                      }`}>
                        {r.is_system ? "System Role" : "Custom"}
                      </span>
                    </CardTitle>
                    <CardDescription className="text-2xs leading-relaxed">{r.description || "No description provided."}</CardDescription>
                  </div>
                  {r.is_system ? (
                    <Lock className="h-4 w-4 text-muted-foreground/60" />
                  ) : (
                    isWritePermitted && (
                      <button
                        onClick={() => handleDelete(r.id)}
                        disabled={deleteRoleMutation.isPending}
                        className="text-rose-500 hover:text-rose-400 hover:bg-rose-500/10 p-1.5 rounded-lg transition-colors cursor-pointer"
                        title="Delete Custom Role"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )
                  )}
                </CardHeader>

                <CardContent className="pt-2">
                  <p className="text-3xs font-bold text-muted-foreground uppercase tracking-wider mb-2">
                    Authorized Permissions ({r.permissions.length})
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {r.permissions.includes("*") ? (
                      <span className="text-3xs bg-primary/10 border border-primary/20 text-primary px-2.5 py-0.5 rounded-full font-semibold">
                        Bypass All Privileges (*)
                      </span>
                    ) : (
                      r.permissions.map((p) => (
                        <span key={p} className="text-3xs bg-accent/20 border border-border text-foreground px-2 py-0.5 rounded-full">
                          {p}
                        </span>
                      ))
                    )}
                  </div>
                </CardContent>
              </div>
            </Card>
          ))
        )}
      </div>

      {/* Modal dialog to create role */}
      <Dialog
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Configure Custom Role"
        description="Establish a new role and choose the explicit set of system permissions to allocate."
      >
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4 max-h-[500px] overflow-y-auto pr-1">
          <Input
            type="text"
            label="Role Identifier Name"
            placeholder="AcademicSupervisor"
            error={errors.name?.message}
            {...register("name")}
          />

          <Input
            type="text"
            label="Description"
            placeholder="E.g., Can review audit records and edit branding metadata."
            error={errors.description?.message}
            {...register("description")}
          />

          {/* Permissions Matrix */}
          <div className="flex flex-col gap-2 mt-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Select Permissions ({selectedPermissions.length} selected)
            </label>
            {errors.permissions && (
              <span className="text-xs text-rose-500 font-medium">{errors.permissions.message}</span>
            )}

            <div className="border border-border rounded-lg bg-background p-3 flex flex-col gap-3 max-h-[220px] overflow-y-auto">
              {permissions.map((p) => (
                <div key={p.name} className="flex items-start gap-3 text-xs select-none">
                  <input
                    type="checkbox"
                    id={`perm-${p.name}`}
                    checked={selectedPermissions.includes(p.name)}
                    onChange={() => handleCheckboxChange(p.name)}
                    className="mt-0.5 h-4 w-4 rounded border-input text-primary focus:ring-primary"
                  />
                  <label htmlFor={`perm-${p.name}`} className="flex-1 flex flex-col cursor-pointer">
                    <span className="font-semibold text-foreground">{p.name}</span>
                    <span className="text-3xs text-muted-foreground mt-0.5">{p.description}</span>
                  </label>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 border-t border-border pt-4 mt-2">
            <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createRoleMutation.isPending}>
              Create Role
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
