import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-lg text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-indigo-600 text-white shadow-sm hover:bg-indigo-700",
        destructive: "bg-red-600 text-white shadow-sm hover:bg-red-700",
        outline: "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 hover:border-slate-300",
        secondary: "bg-slate-100 text-slate-800 hover:bg-slate-200",
        ghost: "text-slate-700 hover:bg-slate-100",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, children, ...props }, ref) => {
    const compClassName = cn(buttonVariants({ variant, size, className }));
    if (asChild && React.Children.count(children) === 1 && React.isValidElement(children)) {
      const child = children as React.ReactElement<{ className?: string; ref?: React.Ref<unknown> }>;
      return React.cloneElement(child, {
        className: cn(child.props.className, compClassName),
        ref: ref as React.Ref<unknown>,
      });
    }
    return (
      <button
        className={compClassName}
        ref={ref}
        {...props}
      >
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
