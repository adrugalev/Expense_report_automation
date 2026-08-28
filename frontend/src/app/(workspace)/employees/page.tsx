"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import type { Employee, EmployeeAccount } from "@/lib/types";
import { useUser } from "@/hooks/use-user";
import { EmployeeDialog, type EmployeeFormData } from "@/features/employees/employee-dialog";
import { EmployeeTable } from "@/features/employees/employee-table";
import { EmployeePasswordDialogs } from "@/features/employees/access-management";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";

function apiPayload(data: EmployeeFormData) {
  return { ...data, company: data.company || null, phone: data.phone || null, email: data.email || null, manager_name: data.manager_name || null, manager_position: data.manager_position || null, short_name: null, default_signatory_name: null, default_signatory_position: null };
}

export default function EmployeesPage() {
  const client = useQueryClient();
  const { data: user } = useUser();
  const canEdit = user?.role === "admin";
  const query = useQuery({ queryKey: ["employees"], queryFn: () => apiFetch<Employee[]>("/employees") });
  const accounts = useQuery({ queryKey: ["employee-accounts"], queryFn: () => apiFetch<EmployeeAccount[]>("/accounts/employees"), enabled: canEdit });
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Employee | null>(null);
  const [passwordAccount, setPasswordAccount] = useState<EmployeeAccount | null>(null);
  const save = useMutation({
    mutationFn: (data: EmployeeFormData) => apiFetch<Employee>(selected ? `/employees/${selected.id}` : "/employees", { method: selected ? "PUT" : "POST", body: JSON.stringify(apiPayload(data)) }),
    onSuccess: () => { client.invalidateQueries({ queryKey: ["employees"] }); client.invalidateQueries({ queryKey: ["employee-accounts"] }); client.invalidateQueries({ queryKey: ["dashboard"] }); setOpen(false); toast.success("Сотрудник сохранён"); },
  });
  const remove = useMutation({ mutationFn: (employee: Employee) => apiFetch<void>(`/employees/${employee.id}`, { method: "DELETE" }), onSuccess: () => { client.invalidateQueries({ queryKey: ["employees"] }); client.invalidateQueries({ queryKey: ["employee-accounts"] }); toast.success("Сотрудник удалён"); } });
  const employees = useMemo(() => (query.data ?? []).filter((item) => `${item.full_name} ${item.position} ${item.company}`.toLowerCase().includes(search.toLowerCase())), [query.data, search]);
  return (
    <>
      <PageHeader title="Сотрудники" description="Сотрудники, реквизиты и доступ к формированию отчётов." action={canEdit ? <Button onClick={() => { setSelected(null); setOpen(true); }}><Plus className="size-4" />Добавить сотрудника</Button> : undefined} />
      <div className="relative mb-4 max-w-sm"><Search className="absolute left-3 top-3 size-4 text-muted" /><Input className="pl-9" placeholder="Найти сотрудника" value={search} onChange={(event) => setSearch(event.target.value)} /></div>
      {query.isLoading ? <LoadingState rows={6} /> : query.error ? <ErrorState message={query.error.message} retry={() => query.refetch()} /> : employees.length ? <EmployeeTable employees={employees} accounts={accounts.data ?? []} accountsLoading={accounts.isLoading} editable={canEdit} onEdit={(employee) => { setSelected(employee); setOpen(true); }} onDelete={(employee) => remove.mutate(employee)} onPassword={setPasswordAccount} /> : <EmptyState title="Сотрудники не найдены" description="Измените поисковый запрос или добавьте новую запись." />}
      {canEdit ? <EmployeePasswordDialogs account={passwordAccount} onClose={() => setPasswordAccount(null)} /> : null}
      <EmployeeDialog open={open} onOpenChange={setOpen} employee={selected} onSubmit={(data) => save.mutate(data)} pending={save.isPending} />
    </>
  );
}
