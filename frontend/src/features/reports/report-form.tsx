"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Building2, Check, ChevronDown, FileCheck2, Gift, Loader2, Plane, Search, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { FileDropzone } from "@/components/file-dropzone";
import { ReceiptTable } from "@/components/receipt-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { apiFetch } from "@/lib/api";
import { useUser } from "@/hooks/use-user";
import type { Employee, Receipt, ReceiptUpload, ReportDetail, ReportPayload, ReportTypeOption } from "@/lib/types";
import { cn } from "@/lib/utils";

const today = () => new Date().toISOString().slice(0, 10);
const giftPurpose = "Создание долгосрочных деловых отношений, укрепление связей с ключевыми клиентами и деловыми партнёрами и формирование корпоративного имиджа и деловой репутации";
const draftKeyPrefix = "expense-report-draft-v1";

const schema = z.object({
  report_type: z.enum(["business_trip", "representative_expenses", "gifts"]),
  employee_id: z.string().min(1, "Выберите сотрудника"),
  report_date: z.string().min(1, "Укажите дату"),
  trip_city: z.string(),
  trip_start_date: z.string(),
  trip_end_date: z.string(),
  purpose: z.string(),
  event_date: z.string(),
  place: z.string(),
  restaurant_name: z.string(),
  counterparty: z.string(),
  meeting_purpose: z.string(),
  meeting_result: z.string(),
  participants_counterparty: z.string(),
  purchase_date: z.string(),
  build_mode: z.enum(["single", "per_receipt", "per_receipt_different_companies"]),
}).superRefine((value, context) => {
  if (value.report_type === "business_trip") {
    if (!value.trip_city.trim()) context.addIssue({ code: "custom", path: ["trip_city"], message: "Укажите город" });
    if (!value.purpose.trim()) context.addIssue({ code: "custom", path: ["purpose"], message: "Укажите цель поездки" });
    if (!value.trip_start_date) context.addIssue({ code: "custom", path: ["trip_start_date"], message: "Укажите дату" });
    if (!value.trip_end_date) context.addIssue({ code: "custom", path: ["trip_end_date"], message: "Укажите дату" });
    if (value.trip_start_date && value.trip_end_date && value.trip_start_date > value.trip_end_date) context.addIssue({ code: "custom", path: ["trip_end_date"], message: "Дата окончания раньше даты начала" });
  }
  if (value.report_type === "representative_expenses" && !value.event_date) {
    context.addIssue({ code: "custom", path: ["event_date"], message: "Укажите дату мероприятия" });
  }
  if (value.report_type === "gifts") {
    if (!value.purchase_date) context.addIssue({ code: "custom", path: ["purchase_date"], message: "Укажите дату покупки" });
    if (!value.purpose.trim()) context.addIssue({ code: "custom", path: ["purpose"], message: "Укажите цель расходов" });
  }
});

type FormValues = z.infer<typeof schema>;

const defaults: FormValues = {
  report_type: "business_trip",
  employee_id: "",
  report_date: today(),
  trip_city: "",
  trip_start_date: today(),
  trip_end_date: today(),
  purpose: "",
  event_date: today(),
  place: "",
  restaurant_name: "",
  counterparty: "",
  meeting_purpose: "",
  meeting_result: "",
  participants_counterparty: "",
  purchase_date: today(),
  build_mode: "single",
};

const reportIcons = { business_trip: Plane, representative_expenses: Building2, gifts: Gift };

function Field({ label, error, children, className }: { label: string; error?: string; children: React.ReactNode; className?: string }) {
  return <label className={cn("block text-sm font-medium", className)}>{label}<div className="mt-1.5">{children}</div>{error ? <span className="mt-1 block text-xs text-danger">{error}</span> : null}</label>;
}

function EmployeePicker({ employees, value, onChange, error }: { employees: Employee[]; value: string; onChange: (id: string) => void; error?: string }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const root = useRef<HTMLDivElement>(null);
  const selected = employees.find((employee) => employee.id === value);
  const matches = employees.filter((employee) => `${employee.full_name} ${employee.position} ${employee.company ?? ""}`.toLowerCase().includes(search.toLowerCase()));
  useEffect(() => {
    const close = (event: MouseEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  return (
    <div ref={root} className="relative">
      <button type="button" className={cn("flex min-h-11 w-full items-center justify-between rounded-md border bg-surface px-3 text-left text-sm", error && "border-danger")} onClick={() => setOpen((current) => !current)} aria-expanded={open}>
        <span className={cn("min-w-0 truncate", !selected && "text-muted")}>{selected ? `${selected.full_name} · ${selected.position}` : "Выберите сотрудника"}</span><ChevronDown className="size-4 shrink-0 text-muted" />
      </button>
      {open ? <div className="absolute z-30 mt-1 w-full rounded-md border bg-surface p-2 shadow-lg">
        <div className="relative"><Search className="absolute left-3 top-2.5 size-4 text-muted" /><Input autoFocus value={search} onChange={(event) => setSearch(event.target.value)} className="pl-9" placeholder="Поиск по ФИО или должности" /></div>
        <div className="mt-2 max-h-64 overflow-y-auto">
          {matches.map((employee) => <button key={employee.id} type="button" className="flex w-full items-start gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-surface-muted" onClick={() => { onChange(employee.id); setOpen(false); setSearch(""); }}>
            <Check className={cn("mt-0.5 size-4 shrink-0 text-primary", value !== employee.id && "invisible")} /><span><span className="block font-medium">{employee.full_name}</span><span className="block text-xs text-muted">{employee.position}</span></span>
          </button>)}
          {!matches.length ? <p className="px-3 py-5 text-center text-sm text-muted">Ничего не найдено</p> : null}
        </div>
      </div> : null}
      {error ? <span className="mt-1 block text-xs text-danger">{error}</span> : null}
    </div>
  );
}

export function ReportForm() {
  const router = useRouter();
  const { data: user } = useUser();
  const draftKey = `${draftKeyPrefix}:${user?.id ?? "anonymous"}`;
  const employeesQuery = useQuery({ queryKey: ["employees"], queryFn: () => apiFetch<Employee[]>("/employees") });
  const typesQuery = useQuery({ queryKey: ["report-types"], queryFn: () => apiFetch<ReportTypeOption[]>("/reports/types") });
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: defaults });
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [uploads, setUploads] = useState<ReceiptUpload[]>([]);
  const [companyParticipants, setCompanyParticipants] = useState<string[]>([]);
  const [draftRestored, setDraftRestored] = useState(false);
  const reportType = form.watch("report_type");
  const selectedEmployee = form.watch("employee_id");
  const employees = employeesQuery.data ?? [];

  useEffect(() => {
    try {
      const raw = localStorage.getItem(draftKey);
      if (raw) {
        const draft = JSON.parse(raw) as { values?: Partial<FormValues>; receipts?: Receipt[]; uploads?: ReceiptUpload[]; participants?: string[] };
        form.reset({ ...defaults, ...draft.values });
        setReceipts(draft.receipts ?? []);
        setUploads(draft.uploads ?? []);
        setCompanyParticipants(draft.participants ?? []);
      }
    } catch { localStorage.removeItem(draftKey); }
    setDraftRestored(true);
  }, [draftKey, form]);

  useEffect(() => {
    if (!draftRestored) return;
    const subscription = form.watch((values) => localStorage.setItem(draftKey, JSON.stringify({ values, receipts, uploads, participants: companyParticipants })));
    localStorage.setItem(draftKey, JSON.stringify({ values: form.getValues(), receipts, uploads, participants: companyParticipants }));
    return () => subscription.unsubscribe();
  }, [companyParticipants, draftKey, draftRestored, form, receipts, uploads]);

  useEffect(() => {
    const expenseType: Receipt["expense_type"] = reportType === "business_trip" ? "такси" : reportType === "representative_expenses" ? "ресторан" : "подарки";
    setReceipts((items) => items.map((item) => item.expense_type === expenseType ? item : { ...item, expense_type: expenseType }));
    form.setValue("build_mode", "single");
    if (reportType === "gifts" && !form.getValues("purpose")) form.setValue("purpose", giftPurpose);
  }, [form, reportType]);

  const receiveUpload = useCallback((upload: ReceiptUpload) => {
    setUploads((items) => [...items, upload]);
    setReceipts((items) => {
      const expenseType: Receipt["expense_type"] = form.getValues("report_type") === "business_trip" ? "такси" : form.getValues("report_type") === "representative_expenses" ? "ресторан" : "подарки";
      const next = [...items, { ...upload.receipt, expense_type: expenseType }];
      const dates = next.map((item) => item.date).filter((date): date is string => Boolean(date)).sort();
      if (dates.length) {
        form.setValue("trip_start_date", dates[0]);
        form.setValue("trip_end_date", dates.at(-1)!);
        form.setValue("event_date", dates[0]);
        form.setValue("purchase_date", dates[0]);
      }
      if (form.getValues("report_type") === "representative_expenses") {
        if (!form.getValues("restaurant_name") && upload.receipt.seller) form.setValue("restaurant_name", upload.receipt.seller);
        if (!form.getValues("place") && upload.receipt.address) form.setValue("place", upload.receipt.address);
      }
      return next;
    });
  }, [form]);

  const removeUpload = useCallback((upload: ReceiptUpload) => {
    setUploads((items) => items.filter((item) => item.id !== upload.id));
    setReceipts((items) => items.filter((item) => item.file_name !== upload.receipt.file_name));
  }, []);

  const suggestMutation = useMutation({
    mutationFn: () => apiFetch<{ counterparty: string; meeting_purpose: string; meeting_result: string; participants_counterparty: string[] }>("/reports/suggestions/representative", { method: "POST", body: JSON.stringify({ signature: `${form.getValues("restaurant_name")} ${form.getValues("place")}`, recent_counterparties: [], meeting_purpose: form.getValues("meeting_purpose") }) }),
    onSuccess: (suggestion) => {
      if (!form.getValues("counterparty")) form.setValue("counterparty", suggestion.counterparty);
      if (!form.getValues("meeting_purpose")) form.setValue("meeting_purpose", suggestion.meeting_purpose);
      if (!form.getValues("meeting_result")) form.setValue("meeting_result", suggestion.meeting_result);
      if (!form.getValues("participants_counterparty")) form.setValue("participants_counterparty", suggestion.participants_counterparty.join("\n"));
      toast.success("Поля дополнены");
    },
    onError: (error) => toast.error(error.message),
  });

  const generateMutation = useMutation({
    mutationFn: (payload: ReportPayload) => apiFetch<ReportDetail>("/reports/generate", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: (report) => {
      localStorage.removeItem(draftKey);
      toast.success("Документы сформированы");
      router.push(`/reports/${report.id}`);
    },
    onError: (error) => toast.error(error.message),
  });

  const total = useMemo(() => receipts.reduce((sum, receipt) => sum + (Number(receipt.amount) || 0), 0), [receipts]);
  const submit = (values: FormValues) => {
    if (!receipts.length) { toast.error("Добавьте хотя бы один чек"); return; }
    const base = { report_type: values.report_type, employee_id: values.employee_id, report_date: values.report_date, receipts, build_mode: values.build_mode };
    let payload: ReportPayload;
    if (values.report_type === "business_trip") payload = { ...base, report_type: "business_trip", build_mode: "single", trip_city: values.trip_city.trim(), trip_start_date: values.trip_start_date, trip_end_date: values.trip_end_date, purpose: values.purpose.trim() };
    else if (values.report_type === "representative_expenses") payload = { ...base, report_type: "representative_expenses", event_date: values.event_date, place: values.place.trim(), restaurant_name: values.restaurant_name.trim(), counterparty: values.counterparty.trim(), meeting_purpose: values.meeting_purpose.trim(), participants_company: companyParticipants, participants_counterparty: values.participants_counterparty.split("\n").map((item) => item.trim()).filter(Boolean), meeting_result: values.meeting_result.trim() };
    else payload = { ...base, report_type: "gifts", build_mode: "single", purchase_date: values.purchase_date, gift_name: "подарочная продукция", gift_quantity: 1, unit_price: (total > 0 ? total : 1).toFixed(2), recipients: [], counterparty: "Подарки", occasion: "", purpose: values.purpose.trim() };
    generateMutation.mutate(payload);
  };

  const options = typesQuery.data ?? [
    { id: "business_trip", name: "Командировка", description: "Такси и поездки в период командировки", accepted_expense_type: "такси" },
    { id: "representative_expenses", name: "Представительские расходы", description: "Деловая встреча и ресторанные чеки", accepted_expense_type: "ресторан" },
    { id: "gifts", name: "Подарки", description: "Приобретение подарочной продукции", accepted_expense_type: "подарки" },
  ] satisfies ReportTypeOption[];

  return <form onSubmit={form.handleSubmit(submit)} className="space-y-9">
    <section aria-labelledby="type-heading"><h2 id="type-heading" className="mb-3 text-base font-semibold">1. Тип отчёта</h2><div className="grid gap-3 md:grid-cols-3">
      {options.map((option) => { const Icon = reportIcons[option.id]; const active = reportType === option.id; return <button key={option.id} type="button" onClick={() => form.setValue("report_type", option.id, { shouldValidate: true })} className={cn("min-h-28 rounded-lg border bg-surface p-4 text-left transition-colors hover:border-primary", active && "border-primary bg-primary-soft")}>
        <div className="flex items-start justify-between"><Icon className={cn("size-5", active ? "text-primary" : "text-muted")} />{active ? <Check className="size-4 text-primary" /> : null}</div><p className="mt-4 text-sm font-semibold">{option.name}</p><p className="mt-1 text-xs text-muted">{option.description}</p>
      </button>; })}
    </div></section>

    <section className="border-t pt-7" aria-labelledby="employee-heading"><h2 id="employee-heading" className="mb-3 text-base font-semibold">2. Сотрудник</h2><div className="max-w-2xl"><EmployeePicker employees={employees} value={selectedEmployee} onChange={(id) => form.setValue("employee_id", id, { shouldValidate: true })} error={form.formState.errors.employee_id?.message} /></div></section>

    <section className="border-t pt-7" aria-labelledby="receipts-heading"><div className="mb-3"><h2 id="receipts-heading" className="text-base font-semibold">3. Чеки</h2><p className="mt-1 text-sm text-muted">Загрузите сканы и проверьте распознанные значения.</p></div><FileDropzone uploads={uploads} onUploaded={receiveUpload} onRemoved={removeUpload} /><div className="mt-5"><ReceiptTable receipts={receipts} onChange={setReceipts} /></div></section>

    <section className="border-t pt-7" aria-labelledby="details-heading"><div className="mb-4"><h2 id="details-heading" className="text-base font-semibold">4. Данные отчёта</h2><p className="mt-1 text-sm text-muted">Поля меняются в зависимости от выбранного типа.</p></div>
      {reportType === "business_trip" ? <div className="grid max-w-4xl gap-4 sm:grid-cols-2">
        <Field label="Город командировки *" error={form.formState.errors.trip_city?.message}><Input {...form.register("trip_city")} placeholder="Москва" /></Field>
        <Field label="Дата составления документов" error={form.formState.errors.report_date?.message}><Input type="date" {...form.register("report_date")} /></Field>
        <Field label="Дата начала командировки" error={form.formState.errors.trip_start_date?.message}><Input type="date" {...form.register("trip_start_date")} /></Field>
        <Field label="Дата окончания командировки" error={form.formState.errors.trip_end_date?.message}><Input type="date" {...form.register("trip_end_date")} /></Field>
        <Field label="Цель поездки *" className="sm:col-span-2" error={form.formState.errors.purpose?.message}><Textarea {...form.register("purpose")} /></Field>
      </div> : null}

      {reportType === "representative_expenses" ? <div className="grid max-w-5xl gap-x-8 gap-y-4 lg:grid-cols-2">
        <div className="space-y-4">
          <Field label="Дата составления документов" error={form.formState.errors.report_date?.message}><Input type="date" {...form.register("report_date")} /></Field>
          <Field label="Дата мероприятия" error={form.formState.errors.event_date?.message}><Input type="date" {...form.register("event_date")} /></Field>
          <Field label="Место проведения"><Input {...form.register("place")} placeholder="Адрес заведения" /></Field>
          <Field label="Название ресторана / кафе"><Input {...form.register("restaurant_name")} /></Field>
          <Field label="Контрагент / организация"><Input {...form.register("counterparty")} /></Field>
          <Field label="Цель встречи"><Textarea {...form.register("meeting_purpose")} /></Field>
          <Field label="Результат встречи"><Textarea {...form.register("meeting_result")} /></Field>
        </div>
        <div className="space-y-5">
          <fieldset><legend className="text-sm font-medium">Участники со стороны компании</legend><div className="mt-2 space-y-1 rounded-lg border p-2">{employees.map((employee) => <label key={employee.id} className="flex cursor-pointer items-start gap-2 rounded-md px-2 py-2 text-sm hover:bg-surface-muted"><input type="checkbox" className="mt-0.5 size-4 accent-primary" checked={companyParticipants.includes(employee.full_name)} onChange={(event) => setCompanyParticipants((current) => event.target.checked ? [...current, employee.full_name] : current.filter((name) => name !== employee.full_name))} /><span><span className="block font-medium">{employee.full_name}</span><span className="text-xs text-muted">{employee.position}</span></span></label>)}</div></fieldset>
          <Field label="Участники со стороны контрагента"><Textarea {...form.register("participants_counterparty")} placeholder="По одному участнику на строку" /></Field>
          <Field label="Способ формирования"><select {...form.register("build_mode")} className="h-10 w-full rounded-md border bg-surface px-3 text-sm"><option value="single">Один документ по всем чекам</option><option value="per_receipt">Отдельный документ на каждый чек</option><option value="per_receipt_different_companies">Отдельно по чекам и организациям</option></select></Field>
          <Button type="button" variant="secondary" onClick={() => suggestMutation.mutate()} disabled={suggestMutation.isPending}><Sparkles className="size-4" />Дополнить пустые поля</Button>
        </div>
      </div> : null}

      {reportType === "gifts" ? <div className="max-w-3xl space-y-4"><div className="grid gap-4 sm:grid-cols-2">
        <Field label="Дата покупки" error={form.formState.errors.purchase_date?.message}><Input type="date" {...form.register("purchase_date")} /></Field>
        <Field label="Дата составления документов" error={form.formState.errors.report_date?.message}><Input type="date" {...form.register("report_date")} /></Field>
      </div><Field label="Цель расходов" error={form.formState.errors.purpose?.message}><Textarea className="min-h-28" {...form.register("purpose")} /></Field></div> : null}
    </section>

    <section className="flex flex-col gap-3 border-t py-5 sm:flex-row sm:items-center sm:justify-between">
      <div className="text-sm"><span className="text-muted">Чеков:</span> <strong>{receipts.length}</strong><span className="mx-2 text-border">|</span><span className="text-muted">Итого:</span> <strong>{total.toLocaleString("ru-RU", { minimumFractionDigits: 2 })} ₽</strong></div>
      <div className="flex gap-2"><Button type="button" variant="secondary" onClick={() => { form.reset(defaults); setReceipts([]); setUploads([]); setCompanyParticipants([]); localStorage.removeItem(draftKey); }}>Очистить</Button><Button type="submit" disabled={generateMutation.isPending || employeesQuery.isLoading}>{generateMutation.isPending ? <Loader2 className="size-4 animate-spin" /> : <FileCheck2 className="size-4" />}Сформировать документы</Button></div>
    </section>
  </form>;
}
