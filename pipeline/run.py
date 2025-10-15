import argparse
from pipeline import watcher, batch_queue, postprocess

def main():
    ap = argparse.ArgumentParser(description='Ageless Pipeline CLI')
    sub = ap.add_subparsers(dest='cmd', required=True)

    sub.add_parser('pair', help='Pair front/back from Scans_Inbox to Scans_Ready')

    q = sub.add_parser('queue', help='Create batch job(s) from Scans_Ready')
    q.add_argument('--batch-size', type=int, default=20)

    p = sub.add_parser('post', help='Post-process a batch id')
    p.add_argument('--job-id', required=True)

    args = ap.parse_args()

    if args.cmd == 'pair':
        moved = watcher.process()
        print(f'Paired {moved} card(s).')
    elif args.cmd == 'queue':
        jobs = batch_queue.build_batches(batch_size=args.batch_size)
        for j in jobs:
            print(j)
    elif args.cmd == 'post':
        out = postprocess.process_batch(args.job_id)
        print(out)

if __name__ == '__main__':
    main()
