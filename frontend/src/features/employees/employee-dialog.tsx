"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import type { Employee } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

const schema = z.object({
  full_name: z.string().min(2, "Укажите ФИО"),
  position: z.string().min(2, "Укажите должность"),
  department: z.string(),
  company: z.string(),
  phone: z.string(),
  email: z.union([z.literal(""), z.email("Некорректный email")]),
  manager_name: z.string(),
  manager_position: z.string(),
});
export type EmployeeFormData = z.infer<typeof schema>;

const emptyValues: EmployeeFormData = { full_name: "", position: "", department: "", company: "", phone: "", email: "", manager_name: "", manager_position: "" };

export function EmployeeDialog({ open, onOpenChange, employee, onSubmit, pending }: { open: boolean; onOpenChange: (open: boolean) => void; employee?: Employee | null; onSubmit: (data: EmployeeFormData) => void; pending?: boolean }) {
  const form = useForm<EmployeeFormData>({ resolver: zodResolver(schema), defaultValues: emptyValues });
  useEffect(() => {
    form.reset(employee ? {
      full_name: employee.full_name,
      position: employee.position,
      department: employee.department,
      company: employee.company ?? "",
      phone: employee.phone ?? "",
      email: employee.email ?? "",
      manager_name: employee.manager_name ?? "",
      manager_position: employee.manager_position ?? "",
    } : emptyValues);
  }, [employee, form, open]);
  const field = (name: keyof EmployeeFormData, label: string, type = "text") => (
    <label className="block text-sm font-medium">{label}<Input type={type} className="mt-1.5" {...form.register(name)} />{form.formState.errors[name] ? <span className="mt-1 block text-xs text-danger">{form.formState.errors[name]?.message}</span> : null}</label>
  );
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogTitle>{employee ? "Редактирование сотрудника" : "Новый сотрудник"}</DialogTitle>
        <DialogDescription>Данные автоматически подставляются в отчёты и документы.</DialogDescription>
        <form className="mt-5 grid gap-4 sm:grid-cols-2" onSubmit={form.handleSubmit(onSubmit)}>
          <div className="sm:col-span-2">{field("full_name", "ФИО")}</div>
          {field("position", "Должность")}{field("department", "Подразделение")}
          <div className="sm:col-span-2">{field("company", "Компания")}</div>
          {field("phone", "Телефон")}{field("email", "Email", "email")}
          {field("manager_name", "Руководитель")}{field("manager_position", "Должность руководителя")}
          <div className="flex justify-end gap-2 sm:col-span-2"><Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>Отмена</Button><Button type="submit" disabled={pending}>{pending ? <Loader2 className="size-4 animate-spin" /> : null}Сохранить</Button></div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
