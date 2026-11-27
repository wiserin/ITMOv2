import { useRef } from 'react';
import { Button } from './Button';
import { TextField, type TextFieldProps } from './TextField';

export type SearchFieldProps = Omit<TextFieldProps,
    'value' | 'defaultValue' | 'onChange' | 'type' | 'ref'
    | 'startAdornment' | 'endAdornment'> & {
    value: string;
    onChange: (value: string) => void;
    clearLabel: string;
};

export function SearchField({
    value, onChange, clearLabel, className = '', ...props
}: SearchFieldProps) {
    const input = useRef<HTMLInputElement>(null);
    return <TextField {...props} ref={input} type="search"
        className={`ui-search ${className}`} value={value}
        onChange={event => onChange(event.target.value)}
        startAdornment={<span className="ui-search__icon"
            aria-hidden="true">⌕</span>}
        endAdornment={value && <Button variant="icon"
            disabled={props.disabled || props.readOnly}
            aria-label={clearLabel}
            onClick={() => {
                onChange('');
                input.current?.focus();
            }}>×</Button>} />;
}
