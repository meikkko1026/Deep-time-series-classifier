import time
#from collections import defaultdict
#from functools import partial
#from multiprocessing import cpu_count
#from pathlib import Path
#from textwrap import dedent
import matplotlib.pyplot as plt
import numpy as np
import random
#import pandas as pd

#from sklearn.externals import joblib
#from sklearn.model_selection import train_test_split
#from sklearn.preprocessing import LabelEncoder, StandardScaler

from ptflops import get_model_complexity_info
from thop import profile

#import torch

from torch import nn
#from torch import optim
from torch.nn import functional as F
#from torch.optim.lr_scheduler import _LRScheduler
#from torch.utils.data import TensorDataset, DataLoader
#import datetime
#import pickle
#from git import Repo

import torch.quantization
from torch.quantization import QuantStub, DeQuantStub

from torchsummary import summary

import pickle

import os
#abspath = os.path.abspath('test_classifier_GPU_load.py')
#dname = os.path.dirname(abspath)
#os.chdir(dname)

os.chdir('/home/bhossein/BMBF project/code_repo')
#os.chdir('C:\Hinkelstien\code_repo')

from my_data_classes import create_datasets_file, create_loaders, smooth, create_datasets_win
import my_net_classes
from my_net_classes import SepConv1d, _SepConv1d, Flatten, parameters
import torch
import pickle
# %% ================ loading data
load_ECG =  torch.load ('raw_x_8K_sync_win2K.pt')
#load_ECG =  torch.load ('raw_x_8K_sync.pt') 
#load_ECG =  torch.load ('raw_x_4k_5K.pt') 
#load_ECG =  torch.load ('raw_x_all.pt') 

#%%===============  loading a learned model

save_name ="2d_6CN_3FC_no_BN_in_FC_long"
#save_name ="2d_6CN_3FC_no_BN_in_FC"
#save_name = "test_full_6conv_long"
#save_name = "test_6conv_v2"
#save_name = "test_full_6conv"
#save_name = "1d_6_conv_qn"
#save_name = "1d_5conv_2FC_qn"
#save_name = "1d_3conv_2FC_v2_seed2"
#save_name = "1d_3conv_2FC_seed2"
#save_name = "1d_3conv_2FC_v2_2K_win"
#save_name = "1d_1_conv_1FC"
#save_name = "1d_3con_2FC_2K_win"
#save_name = "1d_6con_2K_win_2d"
#save_name = "1d_6con_2K_win_test_30"
#save_name = "1d_6con_b512_trim_2K_win"
#save_name = "1d_6con_b512_trim_2K_win_s11"
#save_name = "1d_6con_b512_trim_2K_win_s3"

#save_name = "1d_6con_b512_trim_2K_seed2"
#save_name = "1dconv_b512_t4K"
#save_name = "1dconv_b512_drop1B"
#save_name = "1dconv_b512_drop1"
#save_name = "batch_512_BN_B"
#save_name = "1dconv_b512_BNM_B"
#save_name = "1dconv_b512_BNA_B"
#save_name = "batch_512_BNA"
#save_name = "batch_512_BN"
#save_name = "batch_512_B"
#t_stamp = "_batch_512_11_29_17_03"

#save_name2 = input("Input model to load (currently "+save_name+" is selected) :")
#if save_name2 != '':
#    save_name = save_name2

print(save_name + " is loaded.")

loaded_vars = pickle.load(open("train_"+save_name+"_variables.p","rb"))
#loaded_file = pickle.load(open("variables"+t_stamp+".p","rb"))
#loaded_file = pickle.load(open("variables_ended"+t_stamp+".p","rb"))

params = loaded_vars['params']
epoch = params.epoch
print('epoch: %d ' % (epoch))
seed = params.seed
print('seed: %d ' % (seed))
test_size = params.test_size
np.random.seed(seed)
t_range = params.t_range

#cuda_num = input("cuda number:")
cuda_num = 0   # export CUDA_VISIBLE_DEVICES=x

device = torch.device('cuda:'+str(cuda_num) if torch.cuda.is_available() and cuda_num != 'cpu' else 'cpu')
#device = torch.device('cpu')

raw_x = load_ECG['raw_x']
#raw_x = load_ECG['raw_x'].to(device)
target = load_ECG['target']
data_tag = load_ECG['data_tag']
#data_tag = load_ECG['IDs']
if type(target) != 'torch.Tensor':
    target = torch.tensor(load_ECG['target']).to(device)


dataset_splits = create_datasets_win(raw_x, target, data_tag, test_size, seed=seed, t_range = t_range, device = device)
ecg_datasets = dataset_splits[0:3]
trn_idx, val_idx, tst_idx = dataset_splits[3:6]
#ecg_datasets = create_datasets_file(raw_x, target, test_size, seed=seed, t_range = t_range, device = device)


acc_history = loaded_vars['acc_history']
loss_history = loaded_vars['loss_history']
#ecg_datasets = loaded_split['ecg_datasets']
trn_ds, val_ds, tst_ds = ecg_datasets

batch_size = loaded_vars['params'].batch_size
trn_dl, val_dl, tst_dl = create_loaders(ecg_datasets, bs=batch_size, jobs = 0)
raw_feat = ecg_datasets[0][0][0].shape[0]
raw_size = ecg_datasets[0][0][0].shape[1]
num_classes = 2

#device = ecg_datasets[0].tensors[0].device
#device = torch.device('cuda:4' if torch.cuda.is_available() else 'cpu')

#---------------------  Evaluation function
def evaluate(model, tst_dl, thresh_AF = 3, device = 'cpu'):
    model.to(device)
    s = time.time()
    model.eval()
    correct, total , total_P, = 0, 0, 0
#    TP , FP = 0,0
    
    batch = []
    i_error = []
    list_pred = []
    with torch.no_grad():
        for i_batch, batch in enumerate(tst_dl):
            x_raw, y_batch = [t.to(device) for t in batch]
            list_x = list(range(i_batch*tst_dl.batch_size,min((i_batch+1)*tst_dl.batch_size,len(tst_ds))))
        #    x_raw, y_batch = [t.to(device) for t in batch]
        #    x_raw, y_batch = tst_ds.tensors
            #x_raw, y_batch = [t.to(device) for t in val_ds.tensors]
            out = model(x_raw)
            preds = F.log_softmax(out, dim = 1).argmax(dim=1)
        #    preds = F.log_softmax(out, dim = 1).argmax(dim=1).to('cpu')
            list_pred = np.append(list_pred,preds.tolist())
        #    list_pred = np.append(list_pred,preds.tolist())
            total += y_batch.size(0)
            correct += (preds ==y_batch).sum().item()    
        #    i_error = np.append(i_error,np.where(preds !=y_batch))
            i_error = np.append(i_error,[list_x[i] for i in np.where((preds !=y_batch).to('cpu'))[0]])
        #    TP += ((preds ==y_batch) & (1 ==y_batch)).sum().item()
        #    total_P += (1 ==y_batch).sum().item()
        #    FP += ((preds !=y_batch) & (0 ==y_batch)).sum().item()

    elapsed = time.time() - s
    print('''elapsed time (seconds): {0:.2f}'''.format(elapsed))
        
    acc = correct / total * 100
    #TP_rate = TP / total_P *100
    #FP_rate = FP / (total-total_P) *100
    
    print('Accuracy on all windows of test data:  %2.2f' %(acc))
    
    #TP_rate = TP / (1 ==y_batch).sum().item() *100
    #FP_rate = FP / (0 ==y_batch).sum().item() *100
    
    
    win_size = (data_tag==0).sum()
    # thresh_AF = win_size /2
    # thresh_AF = 3
    
    list_ECG = np.unique([data_tag[i] for i in tst_idx])
    #list_ECG = np.unique([data_tag[i] for i in tst_idx if target[i] == label])
    #len(list_error_ECG)/8000*100
    
    TP_ECG, FP_ECG , total_P, total_N = np.zeros(4)
    list_pred_win = 100*np.ones([len(list_ECG), win_size])
    for i_row, i_ecg in enumerate(list_ECG):
        list_win = np.where(data_tag==i_ecg)[0]
        pred_win = [list_pred[tst_idx.index(i)] for i in list_win]
    #    print(pred_win)
        list_pred_win[i_row,:] = pred_win    
                            
        if i_ecg >8000:   #AF
            total_P +=1
            if (np.array(pred_win)==1).sum() >= thresh_AF:
                TP_ECG += 1                    
        else:         # normal
            total_N +=1
            if (np.array(pred_win)==1).sum() >= thresh_AF:
                FP_ECG += 1
                
        
    #TP_ECG_rate = TP_ECG / len(list_ECG) *100
    TP_ECG_rate = TP_ECG / total_P *100
    FP_ECG_rate = FP_ECG / total_N *100
    
    
    print("Threshold for detecting AF: %d" % (thresh_AF))
    print("TP rate: %2.3f" % (TP_ECG_rate))
    print("FP rate: %2.3f" % (FP_ECG_rate))
    
    return TP_ECG_rate, FP_ECG_rate, list_pred_win, elapsed
#print('True positives on test data:  %2.2f' %(TP_rate))
#print('False positives on test data:  %2.2f' %(FP_rate))
#------------------------------------------  

# %%

#model = my_net_classes.Classifier_1d_1_conv_1FC(raw_feat, num_classes, raw_size).to(device)
#model = my_net_classes.Classifier_1d_3_conv_2FC_v2(raw_feat, num_classes, raw_size).to(device)
#model = my_net_classes.Classifier_1d_3_conv_2FC(raw_feat, num_classes, raw_size, batch_norm = True, conv_type = '2d').to(device)
#model = my_net_classes.Classifier_1d_5_conv_v2(raw_feat, num_classes, raw_size).to(device)
#model = my_net_classes.Classifier_1d_6_conv_v2(raw_feat, num_classes, raw_size).to(device)
#model = my_net_classes.Classifier_1d_6_conv(raw_feat, num_classes, raw_size).to(device)
#model = my_net_classes.Classifier_1d_6_conv_ver1(raw_feat, num_classes, raw_size, batch_norm = True).to(device)
#model = my_net_classes.Classifier_1d_6_conv(raw_feat, num_classes, raw_size, batch_norm = True).to(device)
#model = my_net_classes.Classifier_1dconv(raw_feat, num_classes, raw_size).to(device)
#model = my_net_classes.Classifier_1dconv(raw_feat, num_classes, raw_size, batch_norm = True).to(device)
#model = my_net_classes.Classifier_1dconv_BN(raw_feat, num_classes, raw_size, batch_norm = True).to(device)


#model.load_state_dict(torch.load("train_"+save_name+'_best.pth', map_location=lambda storage, loc: storage))
    
model = pickle.load(open('train_'+save_name+'_best.pth', 'rb'))

#model = Classifier_1dconv(raw_feat, num_classes, raw_size/(2*4**3)).to(device)
#model.load_state_dict(torch.load("train_"+save_name+'_best.pth'))

thresh_AF = 3

TP_ECG_rate, FP_ECG_rate, list_pred_win, elapsed = evaluate(model, tst_dl, thresh_AF = thresh_AF)

#pickle.dump((TP_ECG_rate, FP_ECG_rate, list_pred_win, elapsed),open(save_name+"result.p","wb"))


#%% ------------------------- visualize training curve
f, ax = plt.subplots(1,2, figsize=(12,4))    
ax[0].plot(loss_history, label = 'loss')
ax[0].set_title('Validation Loss History')
ax[0].set_xlabel('Epoch no.')
ax[0].set_ylabel('Loss')
ax[0].grid()

ax[1].plot(smooth(acc_history, 5)[:-2], label='acc')
#ax[1].plot(acc_history, label='acc')
ax[1].set_title('Validation Accuracy History')
ax[1].set_xlabel('Epoch no.')
ax[1].set_ylabel('Accuracy');
ax[1].grid()
#%%-------  FLOPs and params
model = model.to('cpu')
summary(model, input_size=(raw_feat, raw_size), batch_size = batch_size, device = 'cpu')
flops1, params = get_model_complexity_info(model, (raw_feat, raw_size), as_strings=False, print_per_layer_stat=True);
#%%===============  checking internal values
    
# %%==================================================================== 
# ================================== Quantization
# ====================================================================     
model.to('cpu')


# ----------------- Dynamic Quantization

model_qn = torch.quantization.quantize_dynamic(
        model, {nn.Linear, nn.Conv2d} , dtype= torch.qint8
        )

summary(model, input_size=(raw_feat, raw_size), batch_size = batch_size, device = 'cpu')
summary(model_qn, input_size=(raw_feat, raw_size), batch_size = batch_size, device = 'cpu')

#def print_size_of_model(model):
#    torch.save(model.state_dict(), "temp.p")
#    print('Size (MB):', os.path.getsize("temp.p")/1e6)
#    os.remove('temp.p')


#model_qn.to(device)
model_qn.to('cpu');

TP_ECG_rate_q, FP_ECG_rate_q, list_pred_win, elapsed = evaluate(model_qn, tst_dl)


flops1, params = get_model_complexity_info(model, (raw_feat, raw_size), as_strings=False, print_per_layer_stat=True);
flops_q, params_q = get_model_complexity_info(model_qn, (raw_feat, raw_size), as_strings=False, print_per_layer_stat=True);
print('{:<30}  {:<8}'.format('Computational complexity: ', flops_q))
print('{:<30}  {:<8}'.format('Number of parameters: ', params))

#input = torch.randn(1, raw_feat, raw_size)
flops, params = profile(model.to('cpu'), inputs=(torch.randn(1, raw_feat, raw_size), ))





#%%===========  Conv2d quantization

def print_size_of_model(model):
    torch.save(model.state_dict(), "temp.p")
    print('Size (MB):', os.path.getsize("temp.p")/1e6)
    os.remove('temp.p')
    
class ConvBNReLU(nn.Sequential):
    def __init__(self, in_planes, out_planes, kernel_size=3, stride=(1,1), groups=1):
        super().__init__()
        padding = (0,(kernel_size[1] -1) // 2)
        super(ConvBNReLU, self).__init__(
            nn.Conv2d(in_planes, out_planes, kernel_size, stride, padding, groups=groups, bias=False),
            nn.Conv2d(out_planes, out_planes, kernel_size, stride, padding, groups=groups, bias=False),
            nn.BatchNorm2d(out_planes, momentum=0.1),            
#            nn.Dropout(0.5),
            nn.ReLU(inplace=False),
            nn.Dropout(0.5)
        )

class Flatten2(nn.Module):
    """Converts N-dimensional tensor into 'flat' one."""

    def __init__(self, keep_batch_dim=True):
        super().__init__()
        self.keep_batch_dim = keep_batch_dim

    def forward(self, x):
        if self.keep_batch_dim:
            return x.reshape(x.size(0), -1)
        return x.reshape(-1)        

class dumy_CNN(nn.Module):
    def __init__(self, ni, no, raw_size):
        super().__init__()        
        
        self.layers = nn.Sequential(       
#        self.conv = nn.Conv2d(ni, no, (1,8),bias = False)
#        self.convB = ConvBNReLU(ni,no,(1,9))
        ConvBNReLU(ni,no,(1,9)),
        Flatten2(),
#        my_net_classes.Flatten(),
        nn.Linear(raw_size*no, 2)
        )
        self.quant = QuantStub()
        self.dequant = DeQuantStub()
        
    def fuse_model(self):
        for m in self.modules():
            if type(m) == ConvBNReLU:
                torch.quantization.fuse_modules(m, ['1', '2','3'], inplace=True)
#                torch.quantization.fuse_modules(m, ['0', '1', '2'], inplace=True)
       
    def forward(self, x):
        out = self.quant(x)
        out  =  out.unsqueeze(2)
        out  = self.layers(out)
        out  = self.dequant(out)
        return out    

def evaluation1(model_test,tst_dl):
    correct, total = 0, 0
    with torch.no_grad():
        for i_batch, batch in enumerate(tst_dl):
            x_raw, y_batch = [t.to('cpu') for t in batch]
            out = model_test(x_raw)
            preds = F.log_softmax(out, dim = 1).argmax(dim=1)    
            total += y_batch.size(0)
            correct += (preds ==y_batch).sum().item()    
            
    acc = correct / total * 100
    print(acc)    
    return(acc)
    
model_test = dumy_CNN(2,10, 2048)
model_test.eval()

model_test.fuse_model()

model_test.qconfig = torch.quantization.default_qconfig

print(model_test.qconfig)
torch.quantization.prepare(model_test, inplace=True)

# Calibrate with the training set
evaluation1(model_test,tst_dl)
print('Post Training Quantization: Calibration done')

# Convert to quantized model
model_qn = torch.quantization.convert(model_test)
print('Post Training Quantization: Convert done')


evaluation1(model_qn,tst_dl)

#model_qn = torch.quantization.quantize_dynamic(
#        model_test, {nn.Linear, nn.Conv2d} , dtype= torch.qint8
#        )
#print(model_qn)
#model_qn.conv.weight.data[0,0,0,0].item()


summary(model_test, input_size=(raw_feat, raw_size), batch_size = batch_size, device = 'cpu')
summary(model_qn, input_size=(raw_feat, raw_size), batch_size = batch_size, device = 'cpu')

flops, params = get_model_complexity_info(model_test, (raw_feat, raw_size), as_strings=False, print_per_layer_stat=True);
flops_q, params_q = get_model_complexity_info(model_qn, (raw_feat, raw_size), as_strings=False, print_per_layer_stat=True);

#input = torch.randn(1, raw_feat, raw_size)
#flops, params = profile(model_test, inputs=(torch.randn(1, raw_feat, raw_size), ))

#%%===========  static quantization

#import my_net_classes
#num_calibration_batches = 10
#model = my_net_classes.Classifier_1d_6_conv_v2(raw_feat, num_classes, raw_size)
model = pickle.load(open('train_'+save_name+'_best.pth', 'rb'))
model.to('cpu')
model.eval()
#model(x_raw)


def fuse_model(model):
        for m in model.modules():
            if type(m) == my_net_classes.SepConv1d_v4:
                fuse_profile = ['layers.1', 'layers.2', 'layers.3']
#                fuse_profile = ['layers.0.pointwise', 'layers.1', 'layers.2']
                torch.quantization.fuse_modules(m, fuse_profile, inplace=True)
#                torch.quantization.fuse_modules(m, ['0', '1', '2'], inplace=True)
        torch.quantization.fuse_modules(model.FC, [['1','2'],['4','5']], inplace=True)
        return model

fuse_model(model)
#model.fuse_model()
#model.fuse_model2()
model.qconfig = torch.quantization.default_qconfig


print(model.qconfig)
torch.quantization.prepare(model, inplace=True)

#model(x_raw)

# Calibrate with the training set

def evaluation1(model_test,tst_dl, device = 'cpu', num_batch = len(tst_dl)):
    correct, total = 0, 0
    with torch.no_grad():
        print("i_batch:", end =" ")
        for i_batch, batch in enumerate(tst_dl):
            if i_batch%10==0:
                print(i_batch, end =" ")
            x_raw, y_batch = [t.to(device) for t in batch]
            out = model_test(x_raw)
            preds = F.log_softmax(out, dim = 1).argmax(dim=1)    
            total += y_batch.size(0)
            correct += (preds ==y_batch).sum().item() 
            if i_batch >=num_batch:
                acc = correct / total * 100
                return acc
            
    acc = correct / total * 100
    print("")
    print(acc)    
    return acc
    
evaluation1(model,tst_dl)
print('Post Training Quantization: Calibration done')

# Convert to quantized model
model_qn = torch.quantization.convert(model)
print('Post Training Quantization: Convert done')

#print(model_qn(x_raw).shape)

#evaluation1(model_qn,tst_dl)
a = evaluate(model_qn,tst_dl)
print('Post Training Quantization: Calibration done')


#%%===========  per channel static quantization
model_ch = pickle.load(open('train_'+save_name+'_best.pth', 'rb'))
model_ch.to('cpu')
model_ch.eval()
model_ch.fuse_model()
model_ch.qconfig = torch.quantization.get_default_qconfig('fbgemm')
print(model.qconfig)

torch.quantization.prepare(model, inplace=True)
evaluation1(model_ch,tst_dl)
model_qn2 = torch.quantization.convert(model_ch)

evaluation1(model_qn2,tst_dl)
TP_ECG_rate_chq, FP_ECG_rate_chq = evaluate(model_qn2,tst_dl, thresh_AF = 3)

# %%================================== Training aware quantization
model_qta = pickle.load(open('train_'+save_name+'_best.pth', 'rb'))
device = torch.device('cuda:0')

#model_qta.to('cpu')
model_qta = model_qta.to(device)
model_qta.eval()
model_qta.fuse_model()


#device = torch.device('cpu')

#opt = torch.optim.SGD(model_qta.parameters(), lr = 0.0001) 
opt = torch.optim.Adam(model_qta.parameters(), lr=0.001)

criterion = nn.CrossEntropyLoss (reduction = 'sum')

model_qta.qconfig = torch.quantization.get_default_qat_qconfig('fbgemm')

torch.quantization.prepare_qat(model_qta, inplace=True)

ntrain_batches = 100


def train_one_epoch(model, criterion, opt, trn_dl, device, ntrain_batches):
    i = []    
    ls = random.sample(range(len(trn_dl)), ntrain_batches)
    
    model=model.to(device)
    print(next(model.parameters()).is_cuda)
    model.train()
    
    cnt = 0
    epoch_loss = 0
    
    for i, batch in enumerate(trn_dl):
#        break
        if i not in ls:
            continue
        print('.', end = '')
#        print('%d.'%(i), end = '')
        cnt += 1
#        x_raw, y_batch = batch
        x_raw, y_batch = [t.to(device) for t in batch]
        opt.zero_grad()
        out = model (x_raw)
        loss = criterion(out,y_batch)
        epoch_loss += loss.item()
        loss.backward()
        opt.step()
                
        if cnt >= ntrain_batches:
            print('Loss %3.3f' %(epoch_loss / cnt))
            return

    print('Full Loss', epoch_loss / cnt)
    return

evaluation1(model_qta,val_dl,device, 30)
evaluation1(model,val_dl,device, 30)

acc_0 = 0
for nepoch in range(10):
    train_one_epoch(model_qta, criterion, opt, trn_dl, device, ntrain_batches)    
    model_qta.to('cpu')
    if nepoch > 3:
        # Freeze quantizer parameters
        model_qta.apply(torch.quantization.disable_observer)
    if nepoch > 2:
        # Freeze batch norm mean and variance estimates
        model_qta.apply(torch.nn.intrinsic.qat.freeze_bn_stats)

    # Check the accuracy after each epoch
    quantized_model = torch.quantization.convert(model_qta.eval(), inplace=False)
    quantized_model.eval()
#    TP_ECG_rate_taq, FP_ECG_rate_taq,x,y = evaluate(model_qn2,tst_dl)
    acc = evaluation1(quantized_model,val_dl,'cpu', 30)
    print(', Epoch %d : accuracy = %2.2f'%(nepoch,acc))
#    print('Epoch %d :TP rate = %2.2f , FP rate = %2.2f'%(nepoch, TP_ECG_rate_taq, FP_ECG_rate_taq))
    if acc > acc_0:
#        pickle.dump(quantized_model,open("quantized_model.pth",'wb'))
#        torch.jit.save(torch.jit.script(quantized_model), 'quantized_model.pth')
        quantized_model_best = quantized_model
        model_qta_best = model_qta
        acc_0 = acc
#    elif:
        
#quantized_model_best = model_best
#quantized_model = pickle.load(open("quantized_model.pth",'rb'))
acc = evaluation1(quantized_model_best,tst_dl,'cpu', 30)
TP_ECG_rate_taq, FP_ECG_rate_taq,x,y = evaluate(quantized_model_best,tst_dl)

TP_ECG_rate_taq, FP_ECG_rate_taq,x,y = evaluate(model_qta,tst_dl)