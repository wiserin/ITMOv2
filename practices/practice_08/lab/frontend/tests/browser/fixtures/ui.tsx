import { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
    Avatar, Button, Card, Dialog, EmptyState, Feedback,
    Pagination, SearchField, TextField,
} from '../../../src/UI';
import '../../../src/UI/styles/index.css';

function Fixture() {
    const [clicks, setClicks] = useState(0);
    const [loading, setLoading] = useState(false);
    const [search, setSearch] = useState('');
    const [offset, setOffset] = useState(0);
    const [open, setOpen] = useState(false);
    const [second, setSecond] = useState(false);
    const [backdrop, setBackdrop] = useState(true);
    return <>
        <Card>
            <Button onClick={() => setClicks(value => value + 1)}>
                Обычная кнопка
            </Button>
            <Button disabled>Недоступная кнопка</Button>
            <Button loading={loading}
                onClick={() => setClicks(value => value + 1)}>
                Операция
            </Button>
            <Button onClick={() => setLoading(value => !value)}>
                Переключить загрузку
            </Button>
            <output aria-label="Число нажатий">{clicks}</output>
            <p id="external-hint">Внешнее описание</p>
            <TextField label="Имя" name="name" id="custom-name"
                hint="Публичное имя" error="Имя уже занято"
                aria-describedby="external-hint" />
            <TextField label="Дополнительное имя" hint="Необязательно" />
            <TextField label="Ещё одно имя" />
            <SearchField label="Поиск книг" value={search}
                maxLength={5} placeholder="Название книги"
                clearLabel="Очистить книги" onChange={setSearch} />
            <Pagination offset={offset} pageSize={7} totalCount={15}
                onChange={setOffset} />
            <Pagination offset={75} pageSize={25} hasNext={false}
                label="Последняя страница" onChange={setOffset} />
            <Avatar name="Катя" size="sm" />
            <Avatar name="Лена" size="lg" src="/broken-avatar.png" />
            <Avatar name="Фото" src={
                'data:image/svg+xml,' + encodeURIComponent(
                    '<svg xmlns="http://www.w3.org/2000/svg"/>'
                )
            } />
            <Feedback variant="success">Сохранено</Feedback>
            <EmptyState title="Нет записей">Добавьте первую.</EmptyState>
            <Button onClick={() => setOpen(true)}>Открыть диалог</Button>
            <Button onClick={() => setBackdrop(value => !value)}>
                Переключить закрытие по фону
            </Button>
            <Dialog open={open} title="Первый диалог"
                closeOnBackdrop={backdrop} onClose={() => setOpen(false)}>
                <TextField label="Внутри диалога" />
                <Button onClick={() => setSecond(true)}>
                    Второй диалог
                </Button>
            </Dialog>
            <Dialog open={second} title="Второй диалог"
                onClose={() => setSecond(false)}>
                Произвольное содержимое
            </Dialog>
        </Card>
        <aside><label>Обычное поле<input /></label></aside>
    </>;
}

createRoot(document.getElementById('root')!).render(
    <StrictMode><Fixture /></StrictMode>
);
