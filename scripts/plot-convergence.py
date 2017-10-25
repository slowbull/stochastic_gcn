import matplotlib as mpl
mpl.use('Agg')
from matplotlib import pyplot as plt
import os, sys
import numpy as np
import seaborn as sns
import pandas as pd
from time import time
from multiprocessing import Pool

sns.set_style("whitegrid")

datasets   = [('citeseer', 10, (0, 200), (0, 4e4), (0, 8),   (0, 0), (0, 0), (0.64, 0.72)),
              ('cora',     10, (0, 200), (0, 8e4), (0, 10),  (0, 0), (0, 0), (0.725, 0.80)),
              ('pubmed',   10, (0, 200), (0, 4e4), (0, 20),  (0, 0), (0, 0), (0.725, 0.81)),
              ('nell',     10, (0, 400), (0, 6e4), (0, 14),  (0, 0), (0, 0), (0.4, 0.7)),
              ('ppi',      1,  (0, 800), (0, 1e7), (0, 150), (0, 0), (0, 0), (0, 0)),
              ('reddit',   5,  (0, 50),  (0, 1e7), (0, 150), (0, 0), (0, 0), (0.92, 0.97))]

exps1 = [(20, 'False', 'True', True,  '#000000', 'Exact'),               # k
         #(20, 'False', 'True', False,  '#000000', 'Exact'),               # k
         #(20, False, 'Fast', True,  '#FF0000', 'Exact+Det'),           # r
         (1,  'False', 'True', False, '#777777', 'NS'),               # 0.5k
         (1,  'False', 'True', True,  '#0000FF',  'NS+PP'),            # b
         #(1,  False, 'Fast', True,  '#FF00FF',  'NS+PP+Det'),        # (r, b)
         (1,  'True',  'True', True,  '#00FF00',  'CV+PP'),         # g
         #(1,  'True',  'Fast', True,  '#FFFF00',  'NS+PP+CV+Det'),     # (r, g)
         (1,  'TrueD', 'True', True,  '#FF0000',  'CVD+PP')]   
exps2 = [(20, 'False', 'False', True,  '#000000', 'Exact'),
         (1,  'False', 'False', False, '#777777', 'NS'),
         (1,  'False', 'False', True,  '#0000FF',  'NS+PP'),
         (1,  'True',  'False', True,  '#00FF00',  'CV+PP')]
all_exps = [exps1, exps2]
dir='logs'
fig_dir='figs'


def worker(x):
    ndata, data, nexp, exps = x
    data, num_runs, xiterlims, xdatalims, xtimelims, ytrainllims, yvalllims, yvalacclims = data
    # Create figure data_exp_name.pdf
    # name: (iter/data/time) * (training loss, validation loss, validation accuracy)
    cnt = 0
    handles  = []
    losses   = []
    accs     = []
    train_losses = []
    types    = []
    iters    = []
    amt_data = []
    units    = []
    legends  = []
    times    = []
    colors = {}
    
    cnt = 0
    t = time()
    for deg, cv, dropout, pp, style, text in exps:
        if data == 'nell' and not pp:
            continue
        colors[cnt] = style
        legends.append(text)
        my_amt_data = []
        my_time     = []
        for run in range(num_runs):
            log_file = '{}/{}_pp{}_dropout{}_deg{}_cv{}_run{}.log'.format(
                        dir, data, pp, dropout, deg, cv, run)
            print(log_file)
            N = 0
            with open(log_file) as f:
                current_time = 0
                current_data = 0
                lines = f.readlines()
                for line in lines:
                    if line.find('Epoch') != -1:
                        line = line.replace('=', ' ').split()
                        losses.append(float(line[7]))
                        accs.append(float(line[12]) if data=='ppi' else float(line[9]))
                        train_losses.append(float(line[3]))
                        N += 1
                        current_time += float(line[17])-float(line[19])
                        if data=='reddit':
                            current_data += float(line[-1])
                        else:
                            current_data = float(line[-1])
                        if N > len(my_amt_data):
                            my_amt_data.append(current_data)
                        if N > len(my_time):
                            my_time.append(current_time)
                        units.append(run)
    
            #if data=='reddit':
            #    print(text, my_time)
            amt_data.extend(my_amt_data[:N])
            times.extend(my_time[:N])
            iters.extend(range(N))
            types.extend([cnt]*N)
    
        cnt += 1
    
    df = pd.DataFrame(data={'loss': losses, 'acc': accs, 'type': types, 'iter': iters, 'data': amt_data, 'run': units, 'train_loss': train_losses, 'time': times})
    print('Read tooks {} seconds'.format(time()-t))
    #print(df)

    def create_plot(x, xtitle, xlim, y, ytitle, ylim, legend=False, ltext=None):
        plot_name = '{}/{}_{}_{}_{}.pdf'.format(fig_dir, data, nexp, x, y)

        fig, ax = plt.subplots()
        sns.tsplot(data=df, time=x, unit="run", condition="type", value=y, ax=ax, legend=False, color=colors)
        if not(xlim[0]==0 and xlim[1]==0):
            ax.set_xlim(xlim)
        if not(ylim[0]==0 and ylim[1]==0):
            ax.set_ylim(ylim)

        ax.set_xlabel(xtitle)
        ax.set_ylabel(ytitle)
        ax.set_title(data)

        fig.savefig(plot_name)
        os.system('pdfcrop {} {}'.format(plot_name, plot_name))
        print(plot_name)

        if legend:
            lines = ax.get_lines()
            fig, ax = plt.subplots()
            fig.legend(lines, ltext, ncol=5)
            ax.axis('off')
            fig.savefig('legend_{}.pdf'.format(nexp))


    for x, xtitle, xlim in [('iter', 'Number of epochs', xiterlims), ('data', 'Amount of data', xdatalims), ('time', 'Time', xtimelims)]:
        for y, ytitle, ylim in [('train_loss', 'Training loss', ytrainllims), ('loss', 'Validation loss', yvalllims), ('acc', 'Validation accuracy' if data!='ppi' else 'Validation Micro-F1', yvalacclims)]:
            if data=='reddit' and x=='time' and y=='acc':
                create_plot(x, xtitle, xlim, y, ytitle, ylim, True, [e[-1] for e in exps])
            else:
                create_plot(x, xtitle, xlim, y, ytitle, ylim)



tasks = []
for ndata, data in enumerate(datasets):
    for nexp, exps in enumerate(all_exps):
        tasks.append((ndata, data, nexp, exps))

p = Pool(48)
p.map(worker, tasks)

print('Merging files...')
data_exps = []
x_ys      = []

for ndata, data in enumerate(datasets):
    for nexp, exps in enumerate(all_exps):
        data_exps.append((data[0], nexp))

for x in ['iter', 'data', 'time']:
    for y in ['train_loss', 'loss', 'acc']:
        x_ys.append((x, y))


def merge_pdf(x):
    output, input, size = x
    print(output)
    command = "pdfjam --delta '0cm 0cm' --offset '0cm 0cm' --clip true --nup {} {} --outfile {}".format(size, ' '.join(input), output)
    os.system(command)
    os.system("pdfcrop {} {}".format(output, output))


tasks = []
for data, exp in data_exps:
    merged_name = '{}_{}.pdf'.format(data, exp)
    input_names = []
    for x, y in x_ys:
        input_names.append('{}/{}_{}_{}_{}.pdf'.format(fig_dir, data, exp, x, y))
    tasks.append((merged_name, input_names, '3x3'))

for exp in range(len(all_exps)):
    for x, y in x_ys:
        merged_name = '{}_{}_{}.pdf'.format(x, y, exp)
        input_names = []
        for data in datasets:
            input_names.append('{}/{}_{}_{}_{}.pdf'.format(fig_dir, data[0], exp, x, y))
        tasks.append((merged_name, input_names, '3x2'))

p = Pool(48)
p.map(merge_pdf, tasks)
 
for i in range(len(all_exps)):
    f = 'legend_{}.pdf'.format(i)
    os.system('pdfcrop {} {}'.format(f, f))
