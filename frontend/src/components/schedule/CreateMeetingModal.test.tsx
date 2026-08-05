import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import CreateMeetingModal from './CreateMeetingModal';
import { meetings, recurringMeetings, twgs } from '../../services/api';

vi.mock('../../hooks/useRedux', () => ({
    useAppSelector: (selector: (state: unknown) => unknown) => selector({
        auth: { user: { role: 'ADMIN', twg_ids: [] } },
    }),
}));

vi.mock('../../services/api', () => ({
    meetings: { create: vi.fn() },
    recurringMeetings: { create: vi.fn() },
    twgs: { dropdown: vi.fn(), listMembers: vi.fn() },
}));

const activeMembers = [
    { id: '11111111-1111-4111-8111-111111111111', full_name: 'Lazarus Ogero', email: 'lazarusogero1@gmail.com', is_active: true },
    { id: '22222222-2222-4222-8222-222222222222', full_name: 'Lazarus Magwaro', email: 'lazarus.magwaro@africacen.org', is_active: true },
    { id: '33333333-3333-4333-8333-333333333333', full_name: 'Inactive Member', email: 'inactive@example.invalid', is_active: false },
];

function renderModal(props: Partial<React.ComponentProps<typeof CreateMeetingModal>> = {}) {
    return render(
        <CreateMeetingModal
            isOpen
            twgId="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
            onClose={vi.fn()}
            onSuccess={vi.fn()}
            {...props}
        />
    );
}

async function fillRequiredFields(user: ReturnType<typeof userEvent.setup>) {
    await type(user, screen.getByLabelText(/session title/i), 'Selective sync');
    await type(user, screen.getByLabelText(/^date$/i), '2026-08-10');
    await type(user, screen.getByLabelText(/^time$/i), '10:00');
}

async function click(user: ReturnType<typeof userEvent.setup>, element: Element) {
    await act(async () => { await user.click(element); });
}

async function type(user: ReturnType<typeof userEvent.setup>, element: Element, value: string) {
    await act(async () => { await user.type(element, value); });
}

async function select(user: ReturnType<typeof userEvent.setup>, element: Element, value: string) {
    await act(async () => { await user.selectOptions(element, value); });
}

describe('CreateMeetingModal attendance selection', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(twgs.dropdown).mockResolvedValue({ data: [
            { id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', name: 'Energy' },
            { id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', name: 'Agriculture' },
        ] } as never);
        vi.mocked(twgs.listMembers).mockResolvedValue({ data: activeMembers } as never);
        vi.mocked(meetings.create).mockResolvedValue({ data: {} } as never);
        vi.mocked(recurringMeetings.create).mockResolvedValue({ data: {} } as never);
    });

    it('defaults to everyone in the TWG', () => {
        renderModal();
        expect((screen.getByRole('radio', { name: /everyone in this twg/i }) as HTMLInputElement).checked).toBe(true);
        expect(twgs.listMembers).not.toHaveBeenCalled();
    });

    it('loads active members and supports searching in specific mode', async () => {
        const user = userEvent.setup();
        renderModal();
        await click(user, screen.getByRole('radio', { name: /specific twg members/i }));

        const picker = await screen.findByRole('button', { name: /choose twg members/i });
        expect(picker.getAttribute('aria-expanded')).toBe('false');
        expect(screen.queryByRole('searchbox', { name: /search members/i })).toBeNull();
        await click(user, picker);
        expect(await screen.findByRole('checkbox', { name: /lazarus ogero/i })).not.toBeNull();
        expect(screen.queryByText('Inactive Member')).toBeNull();
        await type(user, screen.getByRole('searchbox', { name: /search members/i }), 'Magwaro');
        expect(screen.getByRole('checkbox', { name: /lazarus magwaro/i })).not.toBeNull();
        expect(screen.queryByRole('checkbox', { name: /lazarus ogero/i })).toBeNull();
    });

    it('bounds a large roster to 50 visible results and keeps selected names after closing', async () => {
        const user = userEvent.setup();
        const largeRoster = Array.from({ length: 60 }, (_, index) => ({
            id: `member-${index}`,
            full_name: `Member ${String(index + 1).padStart(2, '0')}`,
            email: `member${index + 1}@example.invalid`,
            is_active: true,
        }));
        vi.mocked(twgs.listMembers).mockResolvedValue({ data: largeRoster } as never);
        renderModal();
        await click(user, screen.getByRole('radio', { name: /specific twg members/i }));

        const picker = await screen.findByRole('button', { name: /choose twg members/i });
        expect(screen.queryByRole('listbox', { name: /twg members/i })).toBeNull();
        await click(user, picker);

        const listbox = await screen.findByRole('listbox', { name: /twg members/i });
        expect(within(listbox).getAllByRole('checkbox')).toHaveLength(50);
        expect(screen.getByText(/showing first 50 of 60/i)).not.toBeNull();
        await click(user, within(listbox).getByRole('checkbox', { name: /member 01/i }));
        await click(user, picker);

        expect(screen.queryByRole('listbox', { name: /twg members/i })).toBeNull();
        expect(screen.getByRole('button', { name: /choose twg members.*1 selected.*member 01/i })).not.toBeNull();
    });

    it('restores everyone as the default when reopened after specific mode', async () => {
        const user = userEvent.setup();
        const view = renderModal();
        await click(user, screen.getByRole('radio', { name: /specific twg members/i }));
        await screen.findByRole('button', { name: /choose twg members/i });

        view.rerender(<CreateMeetingModal isOpen={false} twgId="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" onClose={vi.fn()} onSuccess={vi.fn()} />);
        view.rerender(<CreateMeetingModal isOpen twgId="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" onClose={vi.fn()} onSuccess={vi.fn()} />);

        await waitFor(() => expect((screen.getByRole('radio', { name: /everyone in this twg/i }) as HTMLInputElement).checked).toBe(true));
        expect(screen.queryByRole('searchbox', { name: /search members/i })).toBeNull();
    });

    it('submits selected member IDs for one-off meetings', async () => {
        const user = userEvent.setup();
        renderModal();
        await fillRequiredFields(user);
        await click(user, screen.getByRole('radio', { name: /specific twg members/i }));
        await click(user, await screen.findByRole('button', { name: /choose twg members/i }));
        await click(user, await screen.findByRole('checkbox', { name: /lazarus ogero/i }));
        await click(user, screen.getByRole('button', { name: /schedule session/i }));

        await waitFor(() => expect(meetings.create).toHaveBeenCalledWith(expect.objectContaining({
            attendance_mode: 'specific_twg_members',
            selected_member_ids: [activeMembers[0].id],
        })));
    });

    it('clears stale selections when the TWG changes', async () => {
        const user = userEvent.setup();
        renderModal({ twgId: undefined });
        await screen.findByRole('option', { name: 'Energy' });
        await select(user, screen.getByLabelText(/technical working group/i), 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');
        await click(user, screen.getByRole('radio', { name: /specific twg members/i }));
        await click(user, await screen.findByRole('button', { name: /choose twg members/i }));
        await click(user, await screen.findByRole('checkbox', { name: /lazarus ogero/i }));
        expect(screen.getByRole('button', { name: /choose twg members.*1 selected/i })).not.toBeNull();

        await select(user, screen.getByLabelText(/technical working group/i), 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb');
        await waitFor(() => expect(screen.getByText(/0 selected/i)).not.toBeNull());
        expect(twgs.listMembers).toHaveBeenLastCalledWith('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb');
    });

    it('blocks submission with useful text when no specific member is selected', async () => {
        const user = userEvent.setup();
        renderModal();
        await fillRequiredFields(user);
        await click(user, screen.getByRole('radio', { name: /specific twg members/i }));
        await screen.findByRole('button', { name: /choose twg members/i });

        const submit = screen.getByRole('button', { name: /schedule session/i });
        expect((submit as HTMLButtonElement).disabled).toBe(true);
        expect(screen.getByText(/select at least one twg member/i)).not.toBeNull();
        expect(meetings.create).not.toHaveBeenCalled();
    });

    it('is an accessible dialog, closes on Escape, and restores focus', async () => {
        const user = userEvent.setup();
        const onClose = vi.fn();
        const opener = document.createElement('button');
        document.body.append(opener);
        opener.focus();
        const view = renderModal({ onClose });
        expect(screen.getByRole('dialog', { name: /schedule new session/i })).not.toBeNull();
        expect(document.activeElement).toBe(screen.getByLabelText(/close schedule new session/i));
        await act(async () => { await user.keyboard('{Escape}'); });
        expect(onClose).toHaveBeenCalledOnce();
        view.rerender(<CreateMeetingModal isOpen={false} twgId="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" onClose={onClose} onSuccess={vi.fn()} />);
        expect(document.activeElement).toBe(opener);
        opener.remove();
    });

    it('retries member loading after a failure', async () => {
        const user = userEvent.setup();
        vi.mocked(twgs.listMembers).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ data: activeMembers } as never);
        renderModal();
        await click(user, screen.getByRole('radio', { name: /specific twg members/i }));
        await click(user, await screen.findByRole('button', { name: /choose twg members/i }));
        await click(user, await screen.findByRole('button', { name: /retry/i }));
        expect(await screen.findByRole('checkbox', { name: /lazarus ogero/i })).not.toBeNull();
    });

    it('ignores an out-of-order member response from the previous TWG', async () => {
        const user = userEvent.setup();
        let resolveEnergy!: (value: unknown) => void;
        const energy = new Promise(resolve => { resolveEnergy = resolve; });
        vi.mocked(twgs.listMembers)
            .mockImplementationOnce(() => energy as never)
            .mockResolvedValueOnce({ data: [activeMembers[1]] } as never);
        renderModal({ twgId: undefined });
        await screen.findByRole('option', { name: 'Energy' });
        await select(user, screen.getByLabelText(/technical working group/i), 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');
        await click(user, screen.getByRole('radio', { name: /specific twg members/i }));
        await select(user, screen.getByLabelText(/technical working group/i), 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb');
        await click(user, await screen.findByRole('button', { name: /choose twg members/i }));
        expect(await screen.findByRole('checkbox', { name: /lazarus magwaro/i })).not.toBeNull();
        await act(async () => { resolveEnergy({ data: [activeMembers[0]] }); await energy; });
        expect(screen.queryByRole('checkbox', { name: /lazarus ogero/i })).toBeNull();
    });
});
