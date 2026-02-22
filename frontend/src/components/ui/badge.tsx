import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-indigo-100 text-indigo-800",
        secondary: "border-transparent bg-slate-100 text-slate-700",
        destructive: "border-transparent bg-red-100 text-red-700",
        outline: "text-slate-700 border-slate-300",
        urgent: "border-transparent bg-amber-100 text-amber-800",
        technical: "border-transparent bg-blue-100 text-blue-800",
        billing: "border-transparent bg-emerald-100 text-emerald-800",
        legal: "border-transparent bg-violet-100 text-violet-800",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
