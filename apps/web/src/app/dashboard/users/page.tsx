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
import { UserPlus, Edit2, Trash2, Mail, ShieldAlert, UserCheck } from "lucide-react";
import { User, Role } from "@/types";

// User create validation schema
const userSchema = z.object({
  email: z.string().min(1, "Email is required").email("Invalid email"),
  full_name: z.string().min(2, "Full name must be at least 2 characters"),
  password: z.string().min(6, "Password must be at least 6 characters"),
  role_id: z.string().min(1, "Role is required"),
});

type UserFormValues = z.infer<typeof userSchema>;

export default function UsersPage() {
  const queryClient = useQueryClient();
  const { user: currentUser } = useAuth();
  const { success, error: toastError } = useToast();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);

  // Fetch users list
  const { data: users = [], isLoading: usersLoading } = useQuery<User[]>({
    queryKey: ["users_list"],
    queryFn: () => api.get<User[]>("/users"),
  });

  // Fetch roles list for select dropdown
  const { data: roles = [], isLoading: rolesLoading } = useQuery<Role[]>({
    queryKey: ["roles_list"],
    queryFn: () => api.get<Role[]>("/roles"),
  });

  // Setup form resolver
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<UserFormValues>({
    resolver: zodResolver(userSchema),
  });

  // Create User Mutation
  const createUserMutation = useMutation({
    mutationFn: (data: UserFormValues) => {
      return api.post<User>("/users", {
        ...data,
        tenant_id: currentUser?.tenant_id,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users_list"] });
      success("User Created", "New user has been successfully registered.");
      setModalOpen(false);
      reset();
    },
    onError: (err: any) => {
      toastError("Failed to Create User", err?.detail || "An error occurred.");
    },
  });

  // Delete User Mutation
  const deleteUserMutation = useMutation({
    mutationFn: (userId: string) => {
      return api.delete(`/users/${userId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users_list"] });
      success("User Removed", "User account has been deleted.");
    },
    onError: (err: any) => {
      toastError("Failed to Delete User", err?.detail || "An error occurred.");
    },
  });

  const onSubmit = (data: UserFormValues) => {
    createUserMutation.mutate(data);
  };

  const handleDelete = (userId: string) => {
    if (confirm("Are you sure you want to delete this user?")) {
      deleteUserMutation.mutate(userId);
    }
  };

  // Helper check for role permissions
  const hasPermission = (permName: string) => {
    if (!currentUser?.role?.permissions) return false;
    return currentUser.role.permissions.includes("*") || currentUser.role.permissions.includes(permName);
  };

  const isWritePermitted = hasPermission("users:manage");

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Users Management</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Add and manage members inside your academic tenant.
          </p>
        </div>
        
        {isWritePermitted && (
          <Button onClick={() => { setEditingUser(null); setModalOpen(true); }} className="flex items-center gap-2">
            <UserPlus className="h-4 w-4" /> Add User
          </Button>
        )}
      </div>

      {/* Main List */}
      <Card glass>
        <CardContent className="pt-6">
          {usersLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : users.length === 0 ? (
            <EmptyState
              title="No Users Registered"
              description="Start building your collegiate workspace directory by creating user profiles."
              actionText={isWritePermitted ? "Register First User" : undefined}
              onAction={isWritePermitted ? () => setModalOpen(true) : undefined}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left border-collapse">
                <thead>
                  <tr className="border-b border-border text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    <th className="py-3 px-4">Full Name</th>
                    <th className="py-3 px-4">Email</th>
                    <th className="py-3 px-4">Role Assigned</th>
                    <th className="py-3 px-4">Status</th>
                    {isWritePermitted && <th className="py-3 px-4 text-right">Actions</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {users.map((u) => {
                    const matchedRole = roles.find((r) => r.id === u.role_id);
                    const isSelf = u.id === currentUser?.id;
                    return (
                      <tr key={u.id} className="hover:bg-accent/5 transition-colors">
                        <td className="py-3.5 px-4 font-semibold text-foreground flex items-center gap-2">
                          <div className="h-7 w-7 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold">
                            {u.full_name.charAt(0)}
                          </div>
                          {u.full_name} {isSelf && <span className="text-3xs bg-primary/20 text-primary px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider">You</span>}
                        </td>
                        <td className="py-3.5 px-4 text-muted-foreground">
                          <span className="flex items-center gap-1.5">
                            <Mail className="h-3.5 w-3.5" /> {u.email}
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-semibold bg-accent/20 border border-border text-foreground">
                            {matchedRole?.name || "Loading..."}
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          {u.is_active ? (
                            <span className="inline-flex items-center gap-1 text-emerald-500 font-medium text-xs">
                              <UserCheck className="h-3.5 w-3.5" /> Active
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-rose-500 font-medium text-xs">
                              <ShieldAlert className="h-3.5 w-3.5" /> Inactive
                            </span>
                          )}
                        </td>
                        {isWritePermitted && (
                          <td className="py-3.5 px-4 text-right">
                            <div className="flex justify-end gap-2">
                              <Button
                                variant="danger"
                                size="sm"
                                disabled={isSelf || deleteUserMutation.isPending}
                                onClick={() => handleDelete(u.id)}
                                className="h-8 w-8 p-0 cursor-pointer"
                                title="Remove User"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Creation Modal */}
      <Dialog
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Register New User"
        description="Add a new collegiate member. Make sure to assign the appropriate security role permissions."
      >
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Input
            type="text"
            label="Full Name"
            placeholder="Dr. John Doe"
            error={errors.full_name?.message}
            {...register("full_name")}
          />

          <Input
            type="email"
            label="Email Address"
            placeholder="johndoe@institution.edu"
            error={errors.email?.message}
            {...register("email")}
          />

          <Input
            type="password"
            label="Security Password"
            placeholder="••••••••"
            error={errors.password?.message}
            {...register("password")}
          />

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Assign Role
            </label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              {...register("role_id")}
            >
              <option value="">Select a security role...</option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} ({r.is_system ? "System" : "Custom"})
                </option>
              ))}
            </select>
            {errors.role_id && (
              <span className="text-xs text-rose-500 font-medium">{errors.role_id.message}</span>
            )}
          </div>

          <div className="flex justify-end gap-3 border-t border-border pt-4 mt-2">
            <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createUserMutation.isPending}>
              Create Account
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
