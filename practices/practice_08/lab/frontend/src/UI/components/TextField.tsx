import type { InputHTMLAttributes, ReactNode } from 'react';

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: ReactNode;
};

export function TextField({ label, hint, ...props }: TextFieldProps) {
  return <label>{label}{hint && <span>{hint}</span>}
    <input {...props} />
  </label>;
}
