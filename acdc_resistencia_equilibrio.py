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
cal_array = config['Measurement Config']['calibration'].split(',')
vdc_nominal = float(config['Measurement Config']['voltage']);

#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# functions definitions
def instrument_init():
    # variaveis globais
    global ac_source;
    global dc_source;
    global std;
    global dut;
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

    print("Comunicando com o medidor do padrão no endereço "+config['GPIB']['std']+"...");
    std = rm.open_resource("GPIB0::"+config['GPIB']['std']+"::INSTR");
    #print(std.query("*IDN?"));
    print("OK!\n");

    print("Comunicando com o medidor do objeto no endereço "+config['GPIB']['dut']+"...");
    dut = rm.open_resource("GPIB0::"+config['GPIB']['dut']+"::INSTR");
    print(dut.query("*IDN?"));
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

def ler_std():
    if config['Instruments']['std'] == '182A':
        # x = std.query(":FETCH?")
        # modificado em 02/08/2016
        # agora a funcao ler_std() (e ler_dut)) retornam o valor ja formatado.
        x = std.query(":FETCH?").replace('NDCV','').strip()
    elif config['Instruments']['std'] == '2182A':
        # x = std.query(":FETCH?")
        x = std.query(":FETCH?").strip()
    return x

def ler_dut():
    if config['Instruments']['dut'] == '182A':
        # x = dut.query(":FETCH?")
        x = dut.query(":FETCH?").replace('NDCV','').strip()
    elif config['Instruments']['dut'] == '2182A':
        # x = dut.query(":FETCH?")
        x = dut.query(":FETCH?").strip()
    return x

def print_std(std_readings):
##    if config['Instruments']['std'] == '182A':
##        print("std [mV] {:5.6f}".format(float(std_readings[-1].replace('NDCV','').strip())*1000)) 
##    elif config['Instruments']['std'] == '2182A':
##        print("std [mV] {:5.6f}".format(float(std_readings[-1].strip())*100000))
    print("std [mV] {:5.6f}".format(float(std_readings[-1])*1000))
    return

def print_dut(dut_readings):
##    if config['Instruments']['dut'] == '182A':
##        print("dut [Ω] {:5.6f}".format(float(dut_readings[-1].replace('NDCV','').strip())*1000)) 
##    elif config['Instruments']['dut'] == '2182A':
##        print("dut [Ω] {:5.6f}".format(float(dut_readings[-1].strip())*100000))
    print("dut [Ω] {:5.6f}".format(float(dut_readings[-1])*100000))
    return

def aquecimento(tempo):
    # executa o aquecimento, mantendo a tensão nominal aplicada pelo tempo
    # (em segundos) definido na variavel "tempo"
    dc_source.write("OUT +{:.6f} V".format(vdc_nominal));
    dc_source.write("OUT 0 HZ");
    sw.write_raw(dc);
    time.sleep(tempo);
    return

def n_measure():
    # aplicar a tensao nominal, a tensao nominal + 1%, a tensao nominal -1%
    # observar no programa do renato se utiliza o mesmo calibrador
    std_readings = []

    # valor nominal
    dc_source.write("OUT +{:.6f} V".format(vdc_nominal));
    time.sleep(2); # esperar 2 segundos
    sw.write_raw(dc);
    print("Vdc nominal: +{:.6f} V".format(vdc_nominal))
    time.sleep(wait_time);
    std_readings.append(ler_std())
    print_std(std_readings);
    # valor nominal + 1%
    sw.write_raw(ac);
    time.sleep(2); # esperar 2 segundos
    dc_source.write("OUT +{:.6f} V".format(1.01*vdc_nominal));
    time.sleep(2); # esperar 2 segundos
    sw.write_raw(dc);
    print("Vdc nominal + 1%: +{:.6f} V".format(1.01*vdc_nominal))
    time.sleep(wait_time);
    std_readings.append(ler_std())
    print_std(std_readings);
    # valor nominal -1%
    sw.write_raw(ac);
    time.sleep(2); # esperar 2 segundos
    dc_source.write("OUT +{:.6f} V".format(0.99*vdc_nominal));
    time.sleep(2); # esperar 2 segundos
    sw.write_raw(dc);
    print("Vdc nominal - 1%: +{:.6f} V".format(0.99*vdc_nominal))
    time.sleep(wait_time);
    std_readings.append(ler_std())
    print_std(std_readings);
    
    # valor nominal + 1%
    sw.write_raw(ac);
    time.sleep(2); # esperar 2 segundos
    dc_source.write("OUT +{:.6f} V".format(1.01*vdc_nominal));
    time.sleep(2); # esperar 2 segundos
    sw.write_raw(dc);
    print("Vdc nominal + 1%: +{:.6f} V".format(1.01*vdc_nominal))
    time.sleep(wait_time);
    std_readings.append(ler_std())
    print_std(std_readings);
    
    # valor nominal -1%
    sw.write_raw(ac);
    time.sleep(2); # esperar 2 segundos
    dc_source.write("OUT +{:.6f} V".format(0.99*vdc_nominal));
    time.sleep(2); # esperar 2 segundos
    sw.write_raw(dc);
    print("Vdc nominal - 1%: +{:.6f} V".format(0.99*vdc_nominal))
    time.sleep(wait_time);
    std_readings.append(ler_std())
    print_std(std_readings);
    # cálculo
    sw.write_raw(ac); # mantém chave em ac durante cálculo

##    if config['Instruments']['std'] == '182A':
##        E1 = float(std_readings[0].replace('NDCV','').strip())
##    else:
##        E1 = float(std_readings[0].strip())

    E1 = float(std_readings[0])    
    del std_readings[0]

##    if config['Instruments']['std'] == '182A':
##        deltaE1 = numpy.array([float(a.replace('NDCV','').strip()) for a in std_readings]) - E1;   
##    else:
##        deltaE1 = numpy.array([float(a.strip()) for a in std_readings]) - E1;

    deltaE1 = numpy.array([float(a) for a in std_readings]) - E1;

    V = numpy.array([vdc_nominal*1.01, vdc_nominal*0.99, vdc_nominal*1.01, vdc_nominal*0.99])
    deltaV = numpy.array([vdc_nominal*(0.01), vdc_nominal*(-0.01), vdc_nominal*(0.01), vdc_nominal*(-0.01)])
    N1 = deltaE1/E1 * V/deltaV
    return numpy.mean(N1)

def equilibrio_ac():
    # Algoritmo de equilibrio
    # Esta muito confuso na NIT e no Relatório
    # usar valores medidos de Eacobj e Edcobj ao aplicar Vdc nominal
    # aplicar vac + 0.1% e medir Eacobj
    # aplicar vac - 0.1% e medir Eacobj
    # calcular o valor de equilibrio
    # checar se o valor não é maior que 10% do valor nominal

    # fazer interpolacao igual à implementada no labview
    # Equilibrio.vi
    std_readings = []
    ac_source.write("OUT "+str(freq)+" HZ");
    dc_source.write("OUT {:.6f} V".format(vdc_nominal));
    time.sleep(5) # aguarda 10 segundos antes de iniciar equilibrio
        
    # valor nominal
    sw.write_raw(dc);
    print("Vdc nominal: +{:.6f} V".format(vdc_nominal))
    time.sleep(wait_time/2);
    ac_source.write("OUT {:.6f} V".format(0.999*vac_nominal));
    time.sleep(wait_time/2);
    std_readings.append(ler_std())
    print_std(std_readings);
    # ac - 0.1%
    print("Vac nominal - 0.1%: +{:.6f} V".format(0.999*vac_nominal))
    sw.write_raw(ac);
    time.sleep(wait_time)
    std_readings.append(ler_std())
    print_std(std_readings);
    sw.write_raw(dc);
    time.sleep(2);
    ac_source.write("OUT {:.6f} V".format(1.001*vac_nominal));
    time.sleep(2);
    # ac + 0.1%
    print("Vac nominal + 0.1%: +{:.6f} V".format(1.001*vac_nominal))
    sw.write_raw(ac);
    time.sleep(wait_time)
    std_readings.append(ler_std())
    print_std(std_readings);
    sw.write_raw(dc);

    # calculo do equilibrio
    yp = [0.999*vac_nominal, 1.001*vac_nominal]
    
##    if config['Instruments']['std'] == '182A':
##        xp = [float(std_readings[1].replace('NDCV','').strip()), float(std_readings[2].replace('NDCV','').strip())]
##        xi = float(std_readings[0].replace('NDCV','').strip())
##    else:
##        xp = [float(std_readings[1].strip()), float(std_readings[2].strip())]
##        xi = float(std_readings[0].strip())

    xp = [float(std_readings[1]), float(std_readings[2])]
    xi = float(std_readings[0])
        
    new_ac = numpy.interp(xi,xp,yp);
    
    return new_ac

def equilibrio():
    # inicializa arrays de resultados
    vdc_atual = vdc_nominal;
    ciclo_ac = [];
    Delta = 100;
    while (abs(Delta) > 1):
        std_readings = [];
        # configuracao da fonte AC
        ac_source.write("OUT {:.6f} V".format(vac_atual));
        ac_source.write("OUT "+str(freq)+" HZ");
        # configuracao da fonte DC
        dc_source.write("OUT +{:.6f} V".format(vdc_atual));
        dc_source.write("OUT 0 HZ");
        # Iniciar medicao
        time.sleep(2); # esperar 2 segundos
        if (ciclo_ac == []):
            sw.write_raw(ac);
            print("Ciclo AC")
            time.sleep(wait_time);
            # leituras
            std_readings.append(ler_std())
            print_std(std_readings);
        else:
            print("Ciclo AC")
            std_readings.append(ciclo_ac)
            print_std(std_readings);
        # DC
        sw.write_raw(dc);
        print("Ciclo +DC")
        time.sleep(wait_time);
        std_readings.append(ler_std())
        print_std(std_readings);
        # AC
        sw.write_raw(ac);
        print("Ciclo AC")
        time.sleep(wait_time/2);
        # Mudar fonte DC para -DC
        dc_source.write("OUT -{:.6f} V".format(vdc_atual));
        time.sleep(wait_time/2);
        std_readings.append(ler_std())
        print_std(std_readings);
        # -DC
        sw.write_raw(dc);
        print("Ciclo -DC")
        time.sleep(wait_time);
        std_readings.append(ler_std())
        print_std(std_readings);
        # AC
        sw.write_raw(ac);
        print("Ciclo AC")
        time.sleep(wait_time/2);
        # Mudar fonte DC para +DC
        dc_source.write("OUT +{:.6f} V".format(vdc_atual));
        time.sleep(wait_time/2);
        std_readings.append(ler_std())
        print_std(std_readings);

##        if config['Instruments']['std'] == '182A':
##            x = numpy.array([float(a.replace('NDCV','').strip()) for a in std_readings]);
##        else:
##            x = numpy.array([float(a.strip()) for a in std_readings]);

        x = numpy.array([float(a) for a in std_readings]);

        ac_x = numpy.mean(numpy.array([x[0], x[2], x[4]]));     # AC medio padrao
        dc_x = numpy.mean(numpy.array([x[1], x[3]]));           # DC medio padrao
        delta_x = (ac_x - dc_x) / (N * dc_x);
        Delta = 1e6 * (ac_x - dc_x);
    
    #adj_dc = vdc_atual * (1 + (ac_y - dc_y)/(n_y * dc_y))
        vdc_atual = vdc_atual * (1 + (ac_x - dc_x)/(N * dc_x))
        print("Delta {:.6f}".format(Delta));
        print("Vdc atual {:.6f}".format(vdc_atual));
        if vdc_atual > 1.1*vdc_nominal:
            raise NameError('Tensão DC ajustada perigosamente alta!')
    # corrige com o valor de calibracao da MJ (STD)
    adj_ac = (1 + cal) * vac_atual;
    adj_dc = vdc_atual;

    return [adj_dc, adj_ac]
    
def measure(vdc_atual,vac_atual,ciclo_ac):
    # inicializa arrays de resultados
    dut_readings = []
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
        dut_readings.append(ler_dut())
        print_dut(dut_readings);
    else:
        print("Ciclo AC")
        dut_readings.append(ciclo_ac)
        print_dut(dut_readings);
    # DC
    sw.write_raw(dc);
    print("Ciclo +DC")
    time.sleep(wait_time);
    dut_readings.append(ler_dut())
    print_dut(dut_readings);
    # AC
    sw.write_raw(ac);
    print("Ciclo AC")
    time.sleep(wait_time/2);
    # Mudar fonte DC para -DC
    dc_source.write("OUT -{:.6f} V".format(vdc_atual));
    time.sleep(wait_time/2);
    dut_readings.append(ler_dut())
    print_dut(dut_readings);
    # -DC
    sw.write_raw(dc);
    print("Ciclo -DC")
    time.sleep(wait_time);
    dut_readings.append(ler_dut())
    print_dut(dut_readings);
    # AC
    sw.write_raw(ac);
    print("Ciclo AC")
    time.sleep(wait_time/2);
    # Mudar fonte DC para +DC
    dc_source.write("OUT +{:.6f} V".format(vdc_atual));
    time.sleep(wait_time/2);
    dut_readings.append(ler_dut())
    print_dut(dut_readings);
    return dut_readings

   
def stop_instruments():
    sw.write_raw(reset);
    time.sleep(1)
    ac_source.write("STBY");
    dc_source.write("STBY");
    return

def main():
    try:
        global freq;
        global cal;
        global N;
        global vac_atual;
        global vdc_atual;
              
        print("Inicializando os intrumentos...")
        instrument_init()  # inicializa os instrumentos
        print("Colocando fontes em OPERATE...")
        meas_init()        # inicializa a medicao (coloca fontes em operate)

        print("Aquecimento...")
        aquecimento(heating_time);

        index = 0;
        # fazer loop para cada valor de frequencia
        for value in freq_array:
            freq = float(value) * 1000;
            cal = float(cal_array[index]) * 1e-6;

            print("Medindo o N da MJ...")
            N = n_measure();

            print("Equilibrio AC...");
            vac_atual = equilibrio_ac()

            print("Vac ajustado no equilibrio: {:.6f}".format(vac_atual))
            
            print("Iniciando o algoritmo de equilibrio...")
            adj = equilibrio();
            vdc_atual = adj[0];
            vac_atual = adj[1];
            #vac_atual = vac_nominal;
            #vdc_atual = vdc_nominal;
            print("Vac ajustado com MJ: {:.6f}".format(vac_atual))

            if vac_atual > 1.1*vac_nominal:
                raise NameError('Tensão AC ajustada perigosamente alta!')
            
            print("Iniciando a medição...")
            print("V nominal: {:5.2f} V, f nominal: {:5.2f} Hz".format(vdc_nominal,freq));
           
            first_measure = True;   # flag para determinar se é a primeira repeticao

            print("Iniciando medição...");

             # abrir arquivo para salvar registro
            date = datetime.datetime.now();
            timestamp = datetime.datetime.strftime(date, '%d-%m-%Y_%Hh%Mm%Ss')
            with open(timestamp+"_"+str(freq)+"Hz.csv","w") as csvfile:
                arquivo = csv.writer(csvfile, delimiter=';',lineterminator='\n')
            
                for i in range(0,repeticoes):
                    if first_measure:
                        ciclo_ac = [];
                        first_measure = False
                    else:
                        ciclo_ac = readings[4]
                    readings = measure(vdc_atual,vac_atual,ciclo_ac);
                    arquivo.writerow(["{:5.6f}".format(float(a)*100000).replace('.',',') for a in readings]);
                   
            print("Medição concluída.")
            csvfile.close();
            index += 1;
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
