import { useId, type ComponentProps, type ReactNode } from 'react';

export type TextFieldProps = ComponentProps<'input'> & {
    label: string;
    hint?: ReactNode;
    error?: string;
    startAdornment?: ReactNode;
    endAdornment?: ReactNode;
};

export function TextField({
    label, hint, error, id, className = '',
    startAdornment, endAdornment, ...props
}: TextFieldProps) {
    const generatedId = useId();
    const inputId = id ?? generatedId;
    const hintId = `${inputId}-hint`;
    const errorId = `${inputId}-error`;
    const describedBy = [
        props['aria-describedby'], hint ? hintId : '',
        error ? errorId : '',
    ].filter(Boolean).join(' ') || undefined;

    return <div className={`ui-field ${className}`}>
        <label className="ui-field__label" htmlFor={inputId}>
            {label}
        </label>
        {hint && <span className="ui-field__hint" id={hintId}>
            {hint}
        </span>}
        <div className="ui-field__control">
            {startAdornment}
            <input {...props} id={inputId}
                className="ui-field__input"
                aria-invalid={error ? true : props['aria-invalid']}
                aria-describedby={describedBy} />
            {endAdornment}
        </div>
        {error && <p className="ui-field__error" id={errorId}
            role="alert">{error}</p>}
    </div>;
}
