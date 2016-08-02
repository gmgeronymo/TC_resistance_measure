#-------------------------------------------------------------------------------
# FileName:     novo_acdc.py
# Purpose:      This program measures the resistance of the thermistor of a TC
#
#
# Note:         All dates are in European format DD-MM-YY[YY]
#               This program is compatible with the Thermal Converter with
#               frequency output, currently under development.
#
# Author:       Gean Marcos Geronymo
#
# Created:      21-Jul-2016
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Algoritmo resumido:
# Aplica AC, mede resistencia (tensao)
# Aplica +DC, mede resistencia (tensao)
# Aplica AC, mede resistencia (tensao)
# Aplica -DC, mede resistencia (tensao)
# Aplica AC, mede resistencia (tensao)

# Comandos da chave
# os comandos sao enviados em formato ASCII puro
# utilizar os comandos
# sw.write_raw(chr(2)) (reset)
# sw.write_raw(chr(4)) (ac)
# sw.write_raw(chr(6)) (dc)
# chr(argumento) converte o valor binario em ascii
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# load modules
import visa
import datetime
import configparser
import time
import numpy
import datetime
import csv
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Global constants and variables
# comandos da chave
reset = chr(2)
ac = chr(4)
dc = chr(6)

# configuracoes
# o arquivo settings.ini reune as configuracoes que podem ser alteradas
config = configparser.ConfigParser() # iniciar o objeto config
config.read('settings.ini') # ler o arquivo de configuracao
wait_time = int(config['Measurement Config']['wait_time']); # tempo de espera
heating_time = int(config['Measurement Config']['aquecimento']);
rm = visa.ResourceManager()
repeticoes = int(config['Measurement Config']['repeticoes']);
# Tensao e frequencia nominal
vac_nominal = float(config['Measurement Config']['voltage']);
#freq = float(config['Measurement Config']['frequency']) * 1000;
freq_array = config['Measurement Config']['frequency'].split(',') # array de frequencias
vdc_nominal = float(config['Measurement Config']['voltage']);

#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# functions definitions
def instrument_init():
    # variaveis globais
    global ac_source;
    global dc_source;
    global dvm;
    global sw;
    # Inicialização dos intrumentos conectados ao barramento GPIB
    print("Comunicando com fonte AC no endereço "+config['GPIB']['ac_source']+"...");
    ac_source = rm.open_resource("GPIB0::"+config['GPIB']['ac_source']+"::INSTR");
    print(ac_source.query("*IDN?"));
    print("OK!\n");

    print("Comunicando com fonte DC no endereço "+config['GPIB']['dc_source']+"...");
    dc_source = rm.open_resource("GPIB0::"+config['GPIB']['dc_source']+"::INSTR");
    print(dc_source.query("*IDN?"));
    print("OK!\n");

    print("Comunicando com o medidor do padrão no endereço "+config['GPIB']['dvm']+"...");
    dvm = rm.open_resource("GPIB0::"+config['GPIB']['dvm']+"::INSTR");
    print(dvm.query("*IDN?"));
    print("OK!\n");

    print("Comunicando com a chave no endereço "+config['GPIB']['sw']+"...");
    sw = rm.open_resource("GPIB0::"+config['GPIB']['sw']+"::INSTR");
    sw.write_raw(reset);
    print("OK!\n");

    return

def meas_init():
    # configuracao da fonte AC
    ac_source.write("OUT +{:.6f} V".format(vac_nominal));
    ac_source.write("OUT 1000 HZ");
    # configuracao da fonte DC
    dc_source.write("OUT +{:.6f} V".format(vdc_nominal));
    dc_source.write("OUT 0 HZ");
    # Entrar em OPERATE
    time.sleep(2); # esperar 2 segundos
    ac_source.write("*CLS");
    ac_source.write("OPER");
    dc_source.write("*CLS");
    dc_source.write("OPER");
    time.sleep(10);
    sw.write_raw(ac);
    time.sleep(10);
    return

def ler_dvm():
    if config['Instruments']['dvm'] == '182A':
        x = dvm.query(":FETCH?")
    elif config['Instruments']['dvm'] == '2182A':
        x = dvm.query(":FETCH?")
    return x

def print_dvm(std_readings):
    if config['Instruments']['dvm'] == '182A':
        print("dvm [Ω] {:5.6f}".format(float(std_readings[-1].replace('NDCV','').strip())*1000)) 
    elif config['Instruments']['dvm'] == '2182A':
        print("dvm [Ω] {:5.6f}".format(float(std_readings[-1].strip())*100000))
    return

def aquecimento(tempo):
    # executa o aquecimento, mantendo a tensão nominal aplicada pelo tempo
    # (em segundos) definido na variavel "tempo"
    dc_source.write("OUT +{:.6f} V".format(vdc_nominal));
    dc_source.write("OUT 0 HZ");
    sw.write_raw(dc);
    time.sleep(tempo);
    return

def measure(vdc_atual,vac_atual,ciclo_ac):
    # inicializa arrays de resultados
    dvm_readings = []
    # configuracao da fonte AC
    ac_source.write("OUT {:.6f} V".format(vac_atual));
    ac_source.write("OUT "+str(freq)+" HZ");
    # configuracao da fonte DC
    dc_source.write("OUT +{:.6f} V".format(vdc_atual));
    dc_source.write("OUT 0 HZ");
    # Iniciar medicao
    time.sleep(2); # esperar 2 segundos
    # AC
    if (ciclo_ac == []):
        sw.write_raw(ac);
        print("Ciclo AC")
        time.sleep(wait_time);
        # leituras
        dvm_readings.append(ler_dvm())
        print_dvm(dvm_readings);
    else:
        print("Ciclo AC")
        dvm_readings.append(ciclo_ac)
        print_dvm(dvm_readings);
    # DC
    sw.write_raw(dc);
    print("Ciclo +DC")
    time.sleep(wait_time);
    dvm_readings.append(ler_dvm())
    print_dvm(dvm_readings);
    # AC
    sw.write_raw(ac);
    print("Ciclo AC")
    time.sleep(wait_time/2);
    # Mudar fonte DC para -DC
    dc_source.write("OUT -{:.6f} V".format(vdc_atual));
    time.sleep(wait_time/2);
    dvm_readings.append(ler_dvm())
    print_dvm(dvm_readings);
    # -DC
    sw.write_raw(dc);
    print("Ciclo -DC")
    time.sleep(wait_time);
    dvm_readings.append(ler_dvm())
    print_dvm(dvm_readings);
    # AC
    sw.write_raw(ac);
    print("Ciclo AC")
    time.sleep(wait_time/2);
    # Mudar fonte DC para +DC
    dc_source.write("OUT +{:.6f} V".format(vdc_atual));
    time.sleep(wait_time/2);
    dvm_readings.append(ler_dvm())
    print_dvm(dvm_readings);
    return {'dvm_readings':dvm_readings}

   
def stop_instruments():
    sw.write_raw(reset);
    time.sleep(1)
    ac_source.write("STBY");
    dc_source.write("STBY");
    return

def salvar_arquivo(diferenca,delta):
    date = datetime.datetime.now();
    timestamp = datetime.datetime.strftime(date, '%d-%m-%Y_%Hh%Mm%Ss')
    with open(timestamp+"_"+str(freq)+"Hz.csv","w") as csvfile:
        arquivo = csv.writer(csvfile, delimiter=',',lineterminator='\n')
        for idx, val in enumerate(diferenca):
            arquivo.writerow([str(diferenca[idx]),str(delta[idx])])
        arquivo.writerow([' ',' '])
        arquivo.writerow(["Média: {:5.2f}".format(numpy.mean(diferenca)),"Desvio padrão: {:5.2f}".format(numpy.dvm(diferenca, ddof=1))])
    csvfile.close();
    return


def main():
    try:
        global freq;
        print("Inicializando os intrumentos...")
        instrument_init()  # inicializa os instrumentos
        print("Colocando fontes em OPERATE...")
        meas_init()        # inicializa a medicao (coloca fontes em operate)

        print("Aquecimento...")
        aquecimento(heating_time);

        # fazer loop para cada valor de frequencia
        for value in freq_array:
            freq = float(value) * 1000;
            print("Iniciando a medição...")
            print("V nominal: {:5.2f} V, f nominal: {:5.2f} Hz".format(vdc_nominal,freq));
           
            first_measure = True;   # flag para determinar se é a primeira repeticao

            print("Iniciando medição...");
            
            for i in range(0,repeticoes):
                if first_measure:
                    ciclo_ac = [];
                    first_measure = False
                else:
                    ciclo_ac = readings['dvm_readings'][4]
                readings = measure(vdc_nominal,vac_nominal,ciclo_ac);


            print("Medição concluída.")                      
        
            #print("Resultados:")
            #print("Salvando arquivo...")
            #salvar_arquivo(diff_acdc,Delta)

        stop_instruments()
        print("Concluído.")
                
    except:
        stop_instruments()

    # escrever funcao para a medicao de cada ciclo
    # usar parametros do arquivo de configuracao

# execucao do programa principal
if __name__ == '__main__':
    main()
